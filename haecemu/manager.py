#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator manager
"""

import subprocess
import time
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

    def __init__(self, remote_url=""):
        """Init emulator manager

        :param remote_url: URL of remote frontend
        """
        self._remote_url = remote_url
        self._ctl_prog = None
        self._exp = None

    # --- Cooperate with other components ---

    def _http_put(self, meta_data):
        pass

    def _query_power(self, node):
        pass

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

    # --- Public API ---

    def setup(self, topo, switch=OVSSwitch):
        """Setup an emulation experiment

        :param topo:
        :param switch:
        """
        self._run_controller(topo)
        cluster = maxinet.Cluster()
        self._exp = maxinet.Experiment(cluster, topo, switch=switch)
        self._exp.setup()
        return self._exp

    def cleanup(self):
        """Cleanup an emulation experiment

        :param exp:
        """
        self._exp.stop()
        self._stop_controller()
