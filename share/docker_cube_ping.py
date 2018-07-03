#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Test ping with Cube tology for containers
"""

from haecemu.topolib import CubeTopo
from haecemu.manager import Manager

if __name__ == '__main__':
    topo = CubeTopo()
    mgr = Manager()

    mgr.run_controller(topo)
