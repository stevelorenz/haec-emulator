#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Topology lib for HAEC Emulator
"""

from mininet.topo import Topo


class BaseTopo(Topo):

    """Base topology class"""

    def __init__(self):
        super(BaseTopo, self).__init__()


class CubeTopo(BaseTopo):

    ctl_prog = "ryu_cube.py"

    def build(self):
        pass
