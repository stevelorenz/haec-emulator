#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator
"""

import json
import multiprocessing
import shlex
import subprocess
import time
from os import path
from urlparse import urljoin

import requests

from haecemu import log, topolib
from MaxiNet.Frontend import maxinet
from mininet.node import OVSSwitch

logger = log.logger

CONFIG_ROOT = path.join(path.expanduser("~"), ".haecemu")
CTL_PROG_PATH = path.join(path.expanduser("~"), ".haecemu", "controller")

DEFAULT_CTL_PROG = "ryu_l2_switch.py"

POWER_OUTPUT = u"192.168.0.103:\nP:\t5.34213W\nU:\t4.95125V\nA:\t1.07983A\n\n"

EMU_MODES = ("emu", "test")


class Emulator(object):
    """HAEC Emulator

    Run multiple MaxiNet experiments
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

        self._host_type = None
        self._ctl_prog = None
        self._cluster = None
        self._exp = None
        self._topo = None

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
        workload = self._exp.get_node(host_id).cmd(
            "echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]")
        workload = int(workload.strip())
        return workload

    def _query_power(self, host_id):
        worker_ip = self._exp.get_worker(host_id).ip()
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
            temp = self._exp.get_node(host_id).cmd(
                "cat /sys/devices/virtual/thermal/thermal_zone0/temp").strip()
            temp = int(float(temp) / 1000.0)
        return temp

    def _check_dps_conn(self, num_trys=3, wait=10, restart=False):
        """Check connection of all datapaths (switches) in the topology"""

        topo_dps = self._topo.dpid_table.keys()

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
            wk = self._exp.get_worker(self._topo.dpid_table[dp])
            # MARK: Restart the OVS service to let the Datapath to send hello
            # event again. Events logs can be found ~/.haecemu/log/ryu.log. (Log
            # level should be set to DEBUG in the ryu_log.ini)
            wk.run_cmd("sudo systemctl restart openvswitch-switch.service")
            logger.info("Restart OVS service on worker {}".format(wk.ip()))

    def _get_placement_mapping(self, placement):
        mapping = {}
        # Check if each host has a directly-connected switch
        # https://github.com/MaxiNet/MaxiNet/wiki/Docker-Containers
        for node in self._topo.switches():
            mapping[node] = 0
        logger.debug("[SETUP] Placement mapping: ")
        logger.debug(mapping)
        return mapping

    def _pre_exp_setup(self):

        logger.info(
            "[PRE_EXP_SETUP] Run mininet cleanup on frontend and all workers")

        subprocess.check_call(shlex.split("sudo mn -c"))
        for wk in self._cluster.worker:
            wk.run_cmd("sudo mn -c")

    def _post_cleanup(self):
        self._cluster.remove_all_tunnels()

        logger.info(
            "[POST_CLEANUP] Remove all veth pairs and gre tunnels"
        )
        for wk in self._cluster.worker:
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

            # --- Public API ---

    def setup(self, topo, run_ctl=True,
              dp_wait=30, placement="all_in_one",
              switch=OVSSwitch):
        """Setup an emulation experiment

        :param placement: Placement algorithm
        :param topo: To be emulated network topology
        :param switch:
        """
        self._topo = topo
        self._host_type = topo.host_type
        self._run_ctl = run_ctl
        if self._run_ctl:
            self._run_controller(topo)
        self._cluster = maxinet.Cluster()
        try:
            self._exp = maxinet.Experiment(
                self._cluster, topo, switch=switch,
                nodemapping=self._get_placement_mapping(placement)
            )
            self._pre_exp_setup()
            self._exp.setup()
        except Exception as e:
            logger.error(e)
            self.cleanup()

        self._check_dps_conn(wait=dp_wait)

        return self._exp

    def cleanup(self):
        """Cleanup an emulation experiment"""
        try:
            if self._exp:
                self._exp.stop()
            if self._run_ctl:
                self._stop_controller()
            self._post_cleanup()

        except Exception as e:
            logger.info(e)

        finally:
            # Terminate all worker processes
            logger.info("Terminate all active children processes.")
            for proc in multiprocessing.active_children():
                proc.terminate()
                time.sleep(1)

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

    def mod_processor(self, host_id, opt):
        pass

    def run_task_bg(self, host_id, cmd):
        node = self._exp.get_node(host_id)
        ret = node.cmd("{} > /dev/null 2>&1 &".format(cmd))
        if ret != 0:
            pass

    def stop_task_bg(self, host_id, cmd):
        node = self._exp.get_node(host_id)
        node.cmd("killall {}".format(cmd))

    def _monitor_processor(self, cycle=3):
        """Run monitoring for flows and processors"""
        while True:
            for host_id in self._topo.hosts():
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
        for wk in self._cluster.workers():
            print("Worker IP: {}".format(wk.ip()))
            ret = wk.run_cmd("sudo docker container ls")
            print(ret)
            print("=======")
        print("-------------------------------------------------")

    def ping_all(self):
        sent = 0.0
        received = 0.0
        for host in self._exp.hosts:
            for target in self._exp.hosts:
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
        for h in self._exp.hosts:
            ret = h.cmd("ip -o addr show")
            print("Host: {}".format(h.name))
            print(ret)

    def ping2hosts(self, h1, h2, count=3):
        pass

    def random_iperf_udp(self):
        pass

    def cli(self):
        """CLI"""
        self._exp.CLI(locals(), globals())
