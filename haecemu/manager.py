#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator manager
"""

import subprocess
import time
import urlparse
from os import path

import requests

from haecemu import log
from MaxiNet.Frontend import maxinet
from mininet.node import OVSSwitch

log.conf_logger('DEBUG')

logger = log.logger
CTL_PROG_PATH = path.join(path.expanduser("~"), ".haecemu", "controller")


class Manager(object):
    """HAEC Emulator Manager"""

    _url_create_flow = "communication/create"
    _url_push_processor_info = "processor/info"

    def __init__(self, mode="emu", remote_base_url=""):
        """Init emulator manager

        :param remote_base_url: URL of remote frontend
        """
        self._remote_base_url = remote_base_url
        self._mode = mode

        self._ctl_prog = None
        self._exp = None
        self._topo = None

        logger.debug("API URLs: {}".format(
            ",".join([self._url_create_flow,
                      self._url_push_processor_info
                      ])
        ))

    # --- Cooperate with other components ---

    def _run_controller(self, topo):
        if not hasattr(topo, 'ctl_prog'):
            topo.ctl_prog = 'ryu_l2_switch.py'
        self._ctl_prog = path.join(CTL_PROG_PATH, topo.ctl_prog)
        logger.debug('Current controller program: {}'.format(self._ctl_prog))
        subprocess.check_call(
            "ryu run --observe-links {} & > /dev/null 2>&1".format(
                self._ctl_prog),
            shell=True)
        time.sleep(3)

    def _stop_controller(self):
        subprocess.check_call(
            "sudo killall ryu",
            shell=True)

    # MARK: TBD if check the data validation for each meta-data dict
    def _ck_flow_md(flow_md):
        pass

    def _ck_proc_md(proc_md):
        pass

    def _query_workload(self, proc_id):
        workload = self._exp.get_node(proc_id).cmd(
            "echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]")
        workload = int(workload.strip())
        return workload

    def _query_power(self, proc_id):
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
        self._exp = maxinet.Experiment(cluster, topo, switch=switch)
        self._exp.setup()
        return self._exp

    def install_pkgs(self, extra_pkgs=list()):
        pass

    def cleanup(self):
        """Cleanup an emulation experiment"""
        self._exp.stop()
        self._stop_controller()

    def create_flow(self, flow_md):
        # Check flow metadata

        req_url = urlparse.urljoin(self._remote_base_url, self._url_create_flow)
        r = requests.put(req_url, data=flow_md)
        logger.info("Status code: {}, text: {}".format(r.status_code, r.text))
        if r.status_code != 200:
            raise RuntimeError("Failed to create a new flow.")

    def push_processor(self, proc_id):
        proc_md = {}
        req_url = urlparse.urljoin(self._remote_base_url,
                                   self._url_push_processor_info)
        proc_md['processor_id'] = proc_id
        proc_md['workload'] = self._query_workload(proc_id)
        if self._mode == "test":
            proc_md['temperature'] = 30
            proc_md['power'] = 30
        else:
            pass
        r = requests.put(req_url, data=proc_md)
        logger.info("Status code: {}, text: {}".format(r.status_code, r.text))

    def mod_processor(self, proc_id, opt):
        pass

    def run_task_bg(self, proc_id, cmd):
        node = self._exp.get_node(proc_id)
        ret = node.cmd("{} & > /dev/null 2>&1".format(cmd))

    def stop_task_bg(self, proc_id, cmd):
        node = self._exp.get_node(proc_id)
        node.cmd("killall {}".format(cmd))
