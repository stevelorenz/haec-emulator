#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator
"""

import json
import multiprocessing
import re
import shlex
import subprocess
import time
from os import path
from urlparse import urljoin

import requests

from haecemu import log
from MaxiNet.Frontend import maxinet
from mininet.node import OVSSwitch

logger = log.logger

CONFIG_ROOT = path.join(path.expanduser("~"), ".haecemu")
CTL_PROG_PATH = path.join(path.expanduser("~"), ".haecemu", "controller")

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

    def __init__(self, mode="emu", remote_base_url="",
                 host_type="container"):
        """Init HAEC emulator

        :param remote_base_url: Base URL of the remote frontend
        """
        self._load_config()
        self._remote_base_url = remote_base_url
        if mode not in EMU_MODES:
            logger.error("Invalid emulator mode.")
            self.cleanup()
        self._mode = mode
        self._host_type = "container"

        self._ctl_prog = None
        self._exp = None
        self._topo = None

        logger.debug("API URLs: {}".format(
            ",".join([self._url_create_flow,
                      self._url_push_processor_info
                      ])
        ))

        # Multiproc for tasks
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

    # @staticmethod
    # def _signal_exit(signal, frame):
        # logger.info("Emulator exits.")
        # sys.exit(0)

    # --- SDN Controller ---

    def _run_controller(self, topo):
        """Run controller in background

        Commuinicate with Controller through REST API
        """
        if not hasattr(topo, 'ctl_prog'):
            topo.ctl_prog = 'ryu_l2_switch.py'
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

    # --- Cooperate with other components ---

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

    def _check_dps_conn(self, num_trys=3, wait=10):
        """Check connection of all datapaths (switches) in the topology"""

        topo_sws = self._topo.switches()  # str
        topo_dps = map(int, [re.sub("[^0-9]", "", dp) for dp in topo_sws])

        # a list of int
        t = 0
        while t < num_trys:
            con_dps = self._get_con_dps()
            un_con_dps = list(set(topo_dps) - set(con_dps))
            # All are connected
            if not un_con_dps:
                break
            t += 1
            time.sleep(wait)
        # Too much trys
        else:
            logger.error("""Datapath {} are not connected to the
                            controller""".format(", ".join(map(str, un_con_dps))))
            self.cleanup()

        logger.info("All datapaths are connected to the controller")

    # --- Public API ---

    def map_topo(self, mode="1on1"):
        """Map topology on workers

        :param mode:
        """
        pass

    def setup(self, topo, switch=OVSSwitch):
        """Setup an emulation experiment

        :param topo:
        :param switch:
        """
        self._topo = topo
        self._run_controller(topo)
        cluster = maxinet.Cluster()
        try:
            self._exp = maxinet.Experiment(cluster, topo, switch=switch)
            self._exp.setup()
        except Exception as e:
            logger.error(e)
            self.cleanup()

        self._check_dps_conn()

        return self._exp

    def cleanup(self):
        """Cleanup an emulation experiment"""
        try:
            if self._exp:
                self._exp.stop()
            self._stop_controller()

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

    def cli(self):
        """CLI"""
        while True:
            time.sleep(3)

    def wait(self, sleep=3):
        logger.info("Enter waiting loop...")
        try:
            while True:
                time.sleep(sleep)
        except KeyboardInterrupt:
            return

    # --- Simple Experiments ---

    def ping_all(self):
        sent = 0.0
        received = 0.0
        for host in self._exp.hosts:
            for target in self._exp.hosts:
                if(target == host):
                    continue
                print("{} -> {}".format(host.name, target.name))
                sent += 1.0
                if(host.pexec("ping -c 3 " + target.IP())[2] != 0):
                    print(" X")
                else:
                    received += 1.0
                    print()
        print(
            "Ping All Results: {:.2f} dropped, ({}/{} received)".format(
                (1.0 - received / sent) * 100.0, int(received), int(sent))
        )

    def random_iperf_udp(self):
        pass
