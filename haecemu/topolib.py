#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Topology library for HAEC emulator
"""

import re
from random import randint

from haecemu import log
from MaxiNet.Frontend.container import Docker
from mininet.topo import Topo

logger = log.logger


#  TODO:  <26-07-18, Zuo> Improve these methods #

def rand_byte(max=255):
    return hex(randint(0, max))[2:]


def make_mac(idx):
    return "00:" + rand_byte() + ":" + \
        rand_byte() + ":00:00:" + hex(idx)[2:]


def make_dpid(idx):
    a = make_mac(idx)
    dp = "".join(re.findall(r'[a-f0-9]+', a))
    return "0" * (16 - len(dp)) + dp


class BaseTopo(Topo):

    """Base topology class"""

    def __init__(self, host_type="process",
                 * args, **kwargs):
        self._host_kargs = {}
        if host_type == "docker":
            self._host_kargs["cls"] = Docker
            self._host_kargs["dimage"] = "ubuntu:trusty"
            if "dimage" in kwargs:
                self._host_kargs["dimage"] = kwargs["dimage"]

            logger.info("[TOPO] Use docker containers, with image: {}".format(
                self._host_kargs["dimage"]
            ))
        else:
            logger.info("[TOPO] Use processes.")

        super(BaseTopo, self).__init__(*args, **kwargs)


class SimpleFatTree(BaseTopo):

    ctl_prog = "ryu_l2_switch.py"

    def __init__(self, hosts, bwlimit=10, lat=0.1, * args, **kwargs):
        """Simple fat tree topo with same link latency and bandwidth"""
        self._hosts = hosts
        self._bwlimit = bwlimit
        self._lat = lat
        super(SimpleFatTree, self).__init__(*args, **kwargs)
        logger.info("[TOPO] SimpleFatTree is built.")

    def build(self):
        tor = []
        bw = self._bwlimit
        s = 1
        for i in range(self._hosts):
            h = self.addHost(
                'h' + str(i + 1), mac=make_mac(i),
                ip="10.0.0." + str(i + 1),
                **self._host_kargs
            )
            sw = self.addSwitch('s' + str(s), dpid=make_dpid(s),
                                **dict(listenPort=(13000 + s - 1)))
            s = s + 1
            self.addLink(h, sw, bw=bw, delay=str(self._lat) + "ms")
            tor.append(sw)
        toDo = tor  # nodes that have to be integrated into the tree
        while len(toDo) > 1:
            newToDo = []
            for i in range(0, len(toDo), 2):
                sw = self.addSwitch('s' + str(s), dpid=make_dpid(s),
                                    **dict(listenPort=(13000 + s - 1)))
                s = s + 1
                newToDo.append(sw)
                self.addLink(toDo[i], sw, bw=bw,
                             delay=str(self._lat) + "ms")
                if len(toDo) > (i + 1):
                    self.addLink(toDo[i + 1], sw, bw=bw,
                                 delay=str(self._lat) + "ms")
            toDo = newToDo
            bw = 2.0 * bw


class CubeTopo(BaseTopo):

    ctl_prog = "ryu_cube.py"

    #  TODO:  <26-07-18, Zuo> Extend it to support variable cubic length #
    def __init__(self, length=3, *args, **kwargs):
        if length != 3:
            raise RuntimeError("Currently only support length 3")
        self._length = length
        self.switch_dict = {}
        super(CubeTopo, self).__init__(*args, **kwargs)
        logger.info("[TOPO] CubeTopo is built.")

    def build(self):

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
                        host_name, ip=ip_tpl % (layer, row, col)
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
