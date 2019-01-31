#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator
"""

import json
import multiprocessing
import random
import shlex
import subprocess
import threading
import time
from collections import namedtuple
from os import path
from urlparse import urljoin

import requests

from haecemu import log, topolib, util
from MaxiNet.Frontend import maxinet
from mininet.node import OVSSwitch

logger = log.logger

CONFIG_ROOT = path.join(path.expanduser("~"), ".haecemu")
CTL_PROG_PATH = path.join(path.expanduser("~"), ".haecemu", "controller")

DEFAULT_CTL_PROG = "ryu_l2_switch.py"

POWER_OUTPUT = u"192.168.0.103:\nP:\t5.34213W\nU:\t4.95125V\nA:\t1.07983A\n\n"

EMU_MODES = ("emu", "test")


# Essential information for one experiment
ExpInfo = namedtuple("ExpInfo",
                     ["name", "cluster", "topo", "host_type",
                      "ctl_prog", "placement"])


class Emulator(object):
    """HAEC Emulator

    TODO: Add doc
    """

    # URLs to the GUI frontend
    _url_create_flow = "communication/create"
    _url_push_processor_info = "processor/info"

    _ofctl_url = "http://localhost:8080"

    def __init__(self, mode="emu", remote_base_url=""):
        """Init HAEC emulator

        :param remote_base_url: Base URL of the remote frontend
        """
        self._load_config()
        self._remote_base_url = remote_base_url
        if mode not in EMU_MODES:
            logger.error("Invalid emulator mode.")
            self.cleanup()
        self._mode = mode
        # A cluster can run one Experiment at a time. Several experiment can be
        # run sequentially without destroy/recreating the cluster class
        self._default_cluster = maxinet.Cluster()

        # Current running
        self._cur_cluster = None
        self._cur_exp = None
        self._cur_topo = None

        self._exp_q = list()  # A queue of experiments.

        logger.debug("API URLs: {}".format(
            ",".join([self._url_create_flow,
                      self._url_push_processor_info
                      ])
        ))

        self._worker_procs = []
        self._mon_proc_proc = multiprocessing.Process(name="processor monitor",
                                                      target=self._monitor_processor)
        self._worker_procs.append(self._mon_proc_proc)

    def _load_config(self):
        with open(path.join(CONFIG_ROOT, "config.json")) as config_file:
            configs = json.load(config_file)
        log.conf_logger(level=configs['log']['level'],
                        handler=configs['log']['handler']
                        )

    def _run_controller(self, topo):
        """Run controller in background

        Commuinicate with Controller through REST API
        """
        if not hasattr(topo, "ctl_prog"):
            logger.info(
                "Can not find bound controller program. Use default: {}".format(
                    DEFAULT_CTL_PROG)
            )
            topo.ctl_prog = DEFAULT_CTL_PROG
        self._ctl_prog = path.join(CTL_PROG_PATH, topo.ctl_prog)
        logger.debug('Current controller program: {}'.format(self._ctl_prog))
        subprocess.check_call(
            "ryu-manager --log-config-file {} {} & > /dev/null 2>&1".format(
                path.join(CONFIG_ROOT, "ryu_log.ini"),
                self._ctl_prog),
            shell=True)
        time.sleep(3)
        logger.info("Controller program {} is running.".format(self._ctl_prog))

    def _stop_controller(self):
        subprocess.check_call(
            "sudo killall ryu-manager",
            shell=True)

    def _get_all_flows(self):
        """Get flow stats of all switches"""
        flows = dict()
        r = requests.get(urljoin(self._ofctl_url, '/stats/switches'))
        dps = r.json()
        for dp in dps:
            r = requests.get(
                urljoin(self._ofctl_url, '/stats/flow/{}'.format(dp)))
        return flows

    def _ctl_get_req(self, url):
        return requests.get(urljoin(self._ofctl_url, url)).json()

    def _get_con_dps(self):
        con_dps = self._ctl_get_req("/stats/switches")
        return con_dps

    # MARK: TBD if check the data validation for each meta-data dict

    @staticmethod
    def _ck_flow_md(flow_md):
        pass

    @staticmethod
    def _ck_proc_md(proc_md):
        pass

    def _query_workload(self, host_id):
        # TODO: Replace with a better net based method
        if self._mode == "test":
            random.seed(time.time())
            return (random.random() * 100)
        workload = self._cur_exp.get_node(host_id).cmd(
            "echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]")
        workload = int(workload.strip())
        return workload

    def _query_power(self, host_id):
        worker_ip = self._cur_exp.get_worker(host_id).ip()
        cmd = "ina231_TCP -sample -host {}".format(worker_ip)
        if self._mode == "test":
            out = POWER_OUTPUT
        else:
            out = subprocess.check_output(shlex.split(cmd)).decode('utf-8')
        power = float(out.splitlines()[1][3:-1])
        return power

    def _query_temperature(self, host_id):
        """Query temperature of the remote worker"""
        if self._mode == "test":
            temp = 30
        else:
            temp = self._cur_exp.get_node(host_id).cmd(
                "cat /sys/devices/virtual/thermal/thermal_zone0/temp").strip()
            temp = int(float(temp) / 1000.0)
        return temp

    def _check_dps_conn(self, num_trys=3, wait=10, restart=False):
        """Check connection of all datapaths (switches) in the topology"""

        topo_dps = self._cur_topo.dpid_table.keys()

        t = 0
        while t < num_trys:
            con_dps = map(topolib.dpid_to_str, self._get_con_dps())
            un_con_dps = list(set(topo_dps) - set(con_dps))
            # All are connected
            if not un_con_dps:
                break
            t += 1
            logger.debug("Current connected Datapath: {}".format(
                ", ".join(map(str, con_dps))
            ))
            if restart:
                self._restart_dps(un_con_dps)
            time.sleep(wait)
        # Too much trys
        else:
            logger.error("""Datapath {} are not connected to the
                            controller""".format(", ".join(map(str, un_con_dps))))
            self.cleanup()

        logger.info("All datapaths are connected to the controller")

    def _restart_dps(self, dps):
        """Restart un-connected datapaths"""
        for dp in dps:
            wk = self._cur_exp.get_worker(self._cur_topo.dpid_table[dp])
            # MARK: Restart the OVS service to let the Datapath to send hello
            # event again. Events logs can be found ~/.haecemu/log/ryu.log. (Log
            # level should be set to DEBUG in the ryu_log.ini)
            wk.run_cmd("sudo systemctl restart openvswitch-switch.service")
            logger.info("Restart OVS service on worker {}".format(wk.ip()))

    def _get_placement_mapping(self, placement="round_robin"):
        """ Get placement mapping dict for nodes

        :param placement (str): Placement algorithm
        """
        mapping = {}
        wk_num = len(self._cur_cluster.worker)
        hosts = self._cur_topo.hosts()
        if placement == "round_robin":
            for idx, node in enumerate(self._cur_topo.switches()):
                # Check if each host has a directly-connected switch
                # https://github.com/MaxiNet/MaxiNet/wiki/Docker-Containers
                for h in hosts:
                    if h[1:4] == node[1:4]:
                        mapping[h] = idx % wk_num
                mapping[node] = idx % wk_num

        logger.debug("[SETUP] Placement mapping: %s", json.dumps(mapping))
        return mapping

    def _pre_exp_setup(self):

        logger.info(
            "[PRE_EXP_SETUP] Run mininet cleanup on frontend and all workers")

        subprocess.check_call(shlex.split("sudo mn -c"))
        # Avoid the Ryu manager is not properly closed and address conflicts
        subprocess.run(shlex.split("sudo killall ryu"))
        subprocess.run(shlex.split("sudo killall ryu-manager"))
        for wk in self._cur_cluster.worker:
            wk.run_cmd("sudo mn -c")

    def _post_cleanup(self):
        self._cur_cluster.remove_all_tunnels()

        logger.info(
            "[POST_CLEANUP] Remove all veth pairs and gre tunnels"
        )
        for wk in self._cur_cluster.worker:
            veth_entrys = wk.run_cmd(
                "sudo ip -o link show type veth").splitlines()
            peers = list()
            for entry in veth_entrys:
                veth, peer = entry.split(":")[1].split("@")
                peers.append(peer)
                if veth not in peers:
                    wk.run_cmd("sudo ip link delete {}".format(veth))

            peers = list()
            gre_entrys = wk.run_cmd(
                "sudo ip -o link show type gre").splitlines()
            for entry in gre_entrys:
                gre, peer = entry.split(":")[1].split("@")
                peers.append(peer)
                if gre not in peers:
                    wk.run_cmd("sudo ip link delete {}".format(gre))
                    wk.run_cmd("sudo ip link delete {}tap".format(gre))

    def setup(self):
        pass

    def run_exp(self, exp_info):
        if not exp_info.cluster:
            self._cur_cluster = self._default_cluster
        else:
            self._cur_cluster = exp_info.cluster

        self._cur_topo = exp_info.topo
        exp_obj = self._setup_exp(exp_info)
        self._cur_exp = exp_obj
        return exp_obj

    def stop_cur_exp(self):
        self._cleanup_cur_exp()

    def _setup_exp(self, exp_info):
        self._run_controller(exp_info.topo)
        if not exp_info.placement:
            placement = "round_robin"
        else:
            placement = exp_info.placement

        try:
            cur_exp = maxinet.Experiment(
                self._cur_cluster, exp_info.topo, switch=OVSSwitch,
                nodemapping=self._get_placement_mapping(placement)
            )
            self._pre_exp_setup()
            cur_exp.setup()
        except Exception as e:
            logger.error(e)
            self._cleanup_cur_exp()

        self._check_dps_conn(wait=30)

        return cur_exp

    def cleanup(self):
        # Terminate all worker processes
        logger.info("Terminate all active children processes.")
        for proc in multiprocessing.active_children():
            proc.terminate()
            time.sleep(1)

    def _cleanup_cur_exp(self):
        """Cleanup an emulation experiment"""
        try:
            if self._cur_exp:
                self._cur_exp.stop()
            self._stop_controller()
            self._post_cleanup()

        except Exception as e:
            logger.error(e)
            self.cleanup()

    # TODO: Move fowllowing methods to a subclass or wrapper class of
    # maxinet.Experiment

    def push_flow(self, flow_md):
        """Put a new flow via HTTP put to frontend

        :param flow_md: Flow metadata
        """
        req_url = urljoin(self._remote_base_url, self._url_create_flow)
        r = requests.put(req_url, data=flow_md)
        logger.info("Status code: {}, text: {}".format(r.status_code, r.text))
        if r.status_code != 200:
            raise RuntimeError("Failed to create a new flow.")

    def push_processor(self, host_id):
        """Put a processor info via HTTP put to frontend"""
        proc_md = {}
        req_url = urljoin(self._remote_base_url,
                          self._url_push_processor_info)
        proc_md['processor_id'] = host_id
        proc_md['workload'] = self._query_workload(host_id)
        proc_md['temperature'] = self._query_temperature(host_id)
        proc_md['power'] = self._query_power(host_id)
        r = requests.put(req_url, data=proc_md)
        logger.debug("Status code: {}, text: {}".format(r.status_code, r.text))

    def run_task_bg(self, host_id, cmd, out=None):
        node = self._cur_exp.get_node(host_id)
        if out:
            node.cmd("{} > {} 2>&1 &".format(out, cmd))
        else:
            node.cmd("{} > /dev/null 2>&1 &".format(cmd))

    def stop_task_bg(self, host_id, cmd):
        node = self._cur_exp.get_node(host_id)
        node.cmd("sudo killall {}".format(cmd))

    def _monitor_processor(self, cycle=3):
        """Run monitoring for flows and processors"""
        while True:
            for host_id in self._cur_topo.hosts():
                self.push_processor(host_id)
            time.sleep(3)

    def run_monitor(self, cycle=3):
        """Run monitoring in another process"""
        logger.info("Start monitoring processors")
        self._mon_proc_proc.start()

    def wait(self, sleep=3):
        logger.info("Enter waiting loop...")
        try:
            while True:
                time.sleep(sleep)
        except KeyboardInterrupt:
            return

    def print_docker_status(self):
        """Print docker status of all workers"""
        if self._host_type != "docker":
            logger.info("The host type is not docker")
            return
        print("------ Docker status of all active workers ------")
        for wk in self._cur_cluster.workers():
            print("Worker IP: {}".format(wk.ip()))
            ret = wk.run_cmd("sudo docker container ls")
            print(ret)
            print("=======")
        print("-------------------------------------------------")

    def ping_all(self):
        sent = 0.0
        received = 0.0
        for host in self._cur_exp.hosts:
            for target in self._cur_exp.hosts:
                if(target == host):
                    continue
                logger.info("{} -> {}".format(host.name, target.name))
                sent += 1.0
                if(host.pexec("ping -c 3 " + target.IP())[2] != 0):
                    logger.info("{} can not ping {}".format(
                        host.name, target.name))
                else:
                    received += 1.0
        logger.info(
            "Ping All Results: {:.2f} dropped, ({}/{} received)".format(
                (1.0 - received / sent) * 100.0, int(received), int(sent))
        )

    def print_host_ips(self):
        for h in self._cur_exp.hosts:
            ret = h.cmd("ip -o addr show")
            print("Host: {}".format(h.name))
            print(ret)

    def cli(self):
        """Open MaxiNet CLI"""
        self._cur_exp.CLI(locals(), globals())

    # --- Dev for Service Migration ---

    def swap_ip(self, h1, h2, rp_len=8, add_arp=True):
        """Swap the IP of two hosts

        This is used to change the routing when APPs on two hosts is migrated
        (swapped). After changing IP, the ARP cache is cleared to update mac
        table of the SDN controller
        """
        h2ifce = self._cur_topo.host_ifce_table
        h1_nw = self._cur_exp.get_node(h1)
        h2_nw = self._cur_exp.get_node(h2)
        h1_ip = h1_nw.IP(intf=h2ifce[h1_nw.name])
        h2_ip = h2_nw.IP(intf=h2ifce[h2_nw.name])

        h1_nw.cmd("ip addr flush dev {}".format(h2ifce[h1_nw.name]))
        h1_nw.setIP(h2_ip, intf=h2ifce[h1_nw.name])
        h1_nw.cmd("ip -s -s neigh flush all")

        h2_nw.cmd("ip addr flush dev {}".format(h2ifce[h2_nw.name]))
        h2_nw.setIP(h1_ip, intf=h2ifce[h2_nw.name])
        h2_nw.cmd("ip -s -s neigh flush all")

        # MARK: MAC is unchanged for each host
        if add_arp:
            h1_nw.setARP(h1_ip, h2_nw.MAC())
            h2_nw.setARP(h2_ip, h1_nw.MAC())

    def migrate_server(self, clt, h_prev, h_cur, proc_cmd):
        self.swap_ip(h_prev, h_cur)
        # Client refresh ARP table
        clt_nw = self._cur_exp.get_node(clt)
        clt_nw.cmd("ip -s -s neigh flush all")

        nw = self._cur_exp.get_node(h_prev)
        nw.cmd("sudo killall {}".format(proc_cmd))
        nw = self._cur_exp.get_node(h_cur)
        nw.cmd("{}".format(proc_cmd))

    def _get_host_bw(self, h, h2ifce, bw):
        h_nw = self._cur_exp.get_node(h)
        rx_cmd = "cat /sys/class/net/{}/statistics/rx_bytes".format(h2ifce[h])
        tx_cmd = "cat /sys/class/net/{}/statistics/tx_bytes".format(h2ifce[h])
        rx_prev = int(h_nw.cmd(rx_cmd).strip())
        tx_prev = int(h_nw.cmd(tx_cmd).strip())
        time.sleep(1)
        rx_bw = int(h_nw.cmd(rx_cmd).strip()) - rx_prev  # bytes per second
        tx_bw = int(h_nw.cmd(tx_cmd).strip()) - tx_prev
        bw[h] = (rx_bw, tx_bw)

    @util.print_time_func(logger.debug)
    def get_hosts_bw(self, hosts):
        """Monitor bandwidth of hosts"""
        bw = {}
        h2ifce = self._cur_topo.host_ifce_table
        ths = [threading.Thread(target=self._get_host_bw,
                                args=(h, h2ifce, bw)) for h in hosts]
        for th in ths:
            th.start()

        for th in ths:
            th.join()
        logger.debug("[MONITOR] Bandwidth dict: %s", json.dumps(bw))
        return bw

    # --- Orchestrator Funcs ---
    # TODO: Should be moved to haecemu/orchestrator.py and communicate with IPC

    # --- Only for Debug and Test ---

    def swap_ips_random(self, num=3):
        for n in range(num):
            h1, h2 = random.sample(self._cur_topo.hosts(), 2)
            logger.debug("Round: %s, h1: %s, h2 %s", n, h1, h2)
            self.swap_ip(h1, h2)

    def run_iperf_daemon(self, hosts):
        for h in hosts:
            h_nw = self._cur_exp.get_node(h)
            self.run_task_bg(h, "iperf3 -s {} -D".format(h_nw.IP()))

    def kill_iperf_daemon(self, hosts):
        for h in hosts:
            self.run_task_bg(h, "killall iperf3")

    def run_iperf_udp(self, src, dst, dur=30):
        dst_nw = self._cur_exp.get_node(dst)
        self.run_task_bg(
            src, "iperf3 -c {} -u -t {}".format(dst_nw.IP(), dur)
        )
