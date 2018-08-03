#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator
"""

import json
import shlex
import signal
import subprocess
import sys
import time
from os import path
from urlparse import urljoin

import requests

import ipdb
from haecemu import log, worker
from MaxiNet.Frontend import maxinet
from mininet.node import OVSSwitch

logger = log.logger

CTL_PROG_PATH = path.join(path.expanduser("~"), ".haecemu", "controller")
CONFIG_PATH = path.join(path.expanduser("~"), ".haecemu", "config.json")


# --- Just for tests ---

POWER_OUTPUT = u"192.168.0.103:\nP:\t5.34213W\nU:\t4.95125V\nA:\t1.07983A\n\n"
TEMPERATURE_OUTPUT = u""


class Emulator(object):
    """HAEC Emulator

    Run multiple MaxiNet experiments
    """

    # URLs to the GUI frontend
    _url_create_flow = "communication/create"
    _url_push_processor_info = "processor/info"

    _ofctl_url = "http://localhost:8080"

    def __init__(self, mode="emu", remote_base_url="",
                 host_type="proc"):
        """Init HAEC emulator

        :param remote_base_url: Base URL of the remote frontend
        """
        self._load_config()
        self._remote_base_url = remote_base_url
        self._mode = mode
        self._host_type = "proc"

        self._ctl_prog = None
        self._exp = None
        self._topo = None

        logger.debug("API URLs: {}".format(
            ",".join([self._url_create_flow,
                      self._url_push_processor_info
                      ])
        ))

    def _load_config(self):
        with open(CONFIG_PATH) as config_file:
            configs = json.load(config_file)
        log.conf_logger(level=configs['log']['level'])

    @staticmethod
    def _signal_exit(signal, frame):
        logger.info("Emulator exits.")
        sys.exit(0)

    # --- SDN Controller ---

    def _run_controller(self, topo):
        if not hasattr(topo, 'ctl_prog'):
            topo.ctl_prog = 'ryu_l2_switch.py'
        self._ctl_prog = path.join(CTL_PROG_PATH, topo.ctl_prog)
        logger.debug('Current controller program: {}'.format(self._ctl_prog))
        subprocess.check_call(
            "ryu run {} & > /dev/null 2>&1".format(
                self._ctl_prog),
            shell=True)
        time.sleep(10)
        logger.info("Controller program {} is running.".format(self._ctl_prog))

    def _stop_controller(self):
        subprocess.check_call(
            "sudo killall ryu",
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

    # --- Cooperate with other components ---

    # MARK: TBD if check the data validation for each meta-data dict

    def _ck_flow_md(flow_md):
        pass

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

    # --- Topo Mapping --

    def map_topo(self, mode="1on1"):
        """Map topology on workers

        :param mode:
        """
        pass

    # --- Public API ---

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
            self._stop_controller()
            raise e
        return self._exp

    def install_pkgs(self, extra_pkgs=list()):
        pass

    def cleanup(self):
        """Cleanup an emulation experiment"""
        self._exp.stop()
        self._stop_controller()

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
        logger.info("Status code: {}, text: {}".format(r.status_code, r.text))

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

    def run_monitor(self, cycle=3):
        """Run monitoring for flows and processors"""
        signal.signal(signal.SIGINT, self._signal_exit)
        logger.info("Enter monitoring loop...")
        while True:
            for host_id in self._topo.hosts():
                self.push_processor(host_id)
            time.sleep(3)

        logger.info("Exit monitoring loop")

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
