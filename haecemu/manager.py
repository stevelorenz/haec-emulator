#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator manager
"""

import subprocess

from haecemu import log
from os import path

log.conf_logger('DEBUG')
logger = log.logger

CTL_PROG_PATH = path.join(path.expanduser("~"), ".haecemu", "controller")


class Manager(object):
    """Manager"""

    def __init__(self):
        pass

    def _find_ctl_prog(self, name):
        logger.info("Find controller program in %s", CTL_PROG_PATH)

    def run_controller(self, topo):
        logger.debug("Request controller program: %s", topo.ctl_prog)
        prog_path = self._find_ctl_prog(topo.ctl_prog)

    def build_topo(self, topo):
        pass

    def _http_put(self, flow):
        pass
