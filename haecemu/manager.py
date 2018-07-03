#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: HAEC emulator manager
"""

import subprocess

from haecemu import log

log.conf_logger('DEBUG')
logger = log.logger


class Manager(object):
    """Manager"""

    def __init__(self):
        pass

    def _find_ctl_prog(self, name):
        pass

    def run_controller(self, topo):
        logger.debug("Request controller program: %s", topo.ctl_prog)
        pass

    def build_topo(self, topo):
        pass
