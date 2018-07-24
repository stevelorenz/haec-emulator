#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Topology library for HAEC emulator
"""

from random import randint

from haecemu import log
from MaxiNet.Frontend.container import Docker
from mininet.topo import Topo
from MaxiNet.tools import FatTree

logger = log.logger


class FatTree(FatTree):

    ctl_prog = "ryu_l2_switch.py"

    def __init__(self, *args, **kwargs):
        super(FatTree, self).__init__(*args, **kwargs)
        logger.info("[TOPO] FatTree is built.")


class CubeTopo(Topo):

    ctl_prog = "ryu_cube.py"

    def __init__(self, *args, **kwargs):
        self.switch_dict = {}
        super(CubeTopo, self).__init__(*args, **kwargs)
        logger.info("[TOPO] CubeTopo is built.")

    def build(self, layer_num=3):
        for layer in range(1, 4):
            ip_tpl = '10.%d.%d.%d'
            host_tpl = 'h%d%d%d'
            switch_tpl = 's%d%d%d'
            switch_lt = []
            # Create all hosts and switches, also connections between them
            # Index start from 1
            for row in range(1, 4):
                for col in range(1, 4):
                    host_name = host_tpl % (layer, row, col)
                    new_host = self.addHost(
                        host_name,
                        cls=Docker, dimage="ubuntu:trusty",
                        ip=ip_tpl % (layer, row, col)
                    )
                    switch_name = switch_tpl % (layer, row, col)
                    new_switch = self.addSwitch(
                        switch_name,
                        # MARK: The supported length of DPID in MaxiNet is 12
                        dpid="000000000%d%d%d" % (layer, row, col)
                    )
                    # Add link between host and switches
                    # MARK: - The link between hosts and switches MUST be added before links between switches.
                    #       - The interface name is used for routing. It MUST be given.
                    self.addLink(new_switch, new_host, bw=1,
                                 intfName1=switch_name + "-" + host_name,
                                 intfName2=host_name + "-" + switch_name)
                    switch_lt.append(new_switch)

            self.switch_dict[layer] = switch_lt

            # Add links between switches, with circles
            for i in range(0, 9, 3):
                self.addLink(switch_lt[i], switch_lt[i + 1], bw=1,
                             intfName1=switch_lt[i] + '-' + switch_lt[i + 1],
                             intfName2=switch_lt[i + 1] + '-' + switch_lt[i])

                self.addLink(switch_lt[i + 1], switch_lt[i + 2], bw=1,
                             intfName1=switch_lt[i + 1] +
                             '-' + switch_lt[i + 2],
                             intfName2=switch_lt[i + 2] + '-' + switch_lt[i + 1])

                self.addLink(switch_lt[i], switch_lt[i + 2], bw=1,
                             intfName1=switch_lt[i] + '-' + switch_lt[i + 2],
                             intfName2=switch_lt[i + 2] + '-' + switch_lt[i])

            for i in range(3):
                self.addLink(switch_lt[i], switch_lt[i + 3], bw=1,
                             intfName1=switch_lt[i] + '-' + switch_lt[i + 3],
                             intfName2=switch_lt[i + 3] + '-' + switch_lt[i])

                self.addLink(switch_lt[i + 3], switch_lt[i + 6], bw=1,
                             intfName1=switch_lt[i + 3] +
                             '-' + switch_lt[i + 6],
                             intfName2=switch_lt[i + 6] + '-' + switch_lt[i + 3])

                self.addLink(switch_lt[i], switch_lt[i + 6], bw=1,
                             intfName1=switch_lt[i] + '-' + switch_lt[i + 6],
                             intfName2=switch_lt[i + 6] + '-' + switch_lt[i])

        links = {}
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    # select current node
                    sname = 's%d%d%d' % (i + 1, j + 1, k + 1)
                    # randomly select other nodes
                    for n in ['s%d%d%d' % (1 + (i + 1) % 3, randint(1, 3), randint(1, 3)), 's%d%d%d' % (1 + (i + 2) % 3, randint(1, 3), randint(1, 3))]:
                        if not n + "-" + sname in links:
                            links[sname + "-" + n] = True
                            links[n + "-" + sname] = True
                            self.addLink(sname, n, intfName1=sname +
                                         "-" + n, intfName2=n + "-" + sname, bw=1)
