#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Topology library for HAEC emulator

MARK:
    - Mininet.TCLink:
        - bw: Mbps, delay: ms, loss: %, max_queue_size: n
"""

import re
from random import randint

from haecemu import log
from mininet.topo import Topo

logger = log.logger

try:
    from MaxiNet.Frontend.container import Docker
except ImportError:
    logger.info("[WARN] Can not import docker container for MaxiNet")

HOST_TYPES = ["process", "docker"]

DPID_LEN = 16


def rand_byte(max=255):
    return hex(randint(0, max))[2:]


def make_mac(idx):
    return "00:" + rand_byte() + ":" + \
        rand_byte() + ":00:00:" + hex(idx)[2:]


def make_dpid(idx):
    a = make_mac(idx)
    dp = "".join(re.findall(r'[a-f0-9]+', a))
    return "0" * (DPID_LEN - len(dp)) + dp


def make_dpid_seq(idx):
    dp = "".join(("0" * (DPID_LEN - len(str(idx))), str(idx)))
    return dp


class BaseTopo(Topo):

    """Base topology class"""

    def __init__(self, host_type="process",
                 * args, **kwargs):
        if host_type not in HOST_TYPES:
            logger.error("Invalid host type, support host types {}".format(
                ", ".join(HOST_TYPES)))
            raise RuntimeError
        self.host_type = host_type
        self._host_kargs = {}
        if host_type == "docker":
            self._host_kargs["cls"] = Docker
            # TODO: configure image in config file
            self._host_kargs["dimage"] = "ubuntu:trusty"
            if "dimage" in kwargs:
                self._host_kargs["dimage"] = kwargs["dimage"]

            logger.info("[TOPO] Use docker containers, with image: {}".format(
                self._host_kargs["dimage"]
            ))
        else:
            logger.info("[TOPO] Use processes.")

        super(BaseTopo, self).__init__(*args, **kwargs)


class SingleParentTree(BaseTopo):
    """SingleParentTree

    Mainly used for checking the connectivity of active MaxiNet workers
    """

    ctl_prog = "ryu_l2_switch.py"

    def __init__(self, hosts, bw=10, lat=0.1, *args, **kwargs):
        self._hosts = hosts
        self._bw = bw
        self._lat = lat
        super(SingleParentTree, self).__init__(*args, **kwargs)
        logger.info("[TOPO] SingleParentTree is built")

    def build(self):
        pass


class SimpleFatTree(BaseTopo):

    ctl_prog = "ryu_l2_switch.py"

    def __init__(self, hosts, bwlimit=10, lat=0.1, *args, **kwargs):
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
            sw = self.addSwitch('s' + str(s), dpid=make_dpid_seq(s),
                                **dict(listenPort=(13000 + s - 1)))
            s = s + 1
            self.addLink(h, sw, bw=bw, delay=str(self._lat) + "ms")
            tor.append(sw)
        toDo = tor  # nodes that have to be integrated into the tree
        while len(toDo) > 1:
            newToDo = []
            for i in range(0, len(toDo), 2):
                sw = self.addSwitch('s' + str(s), dpid=make_dpid_seq(s),
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


class HAECCube(BaseTopo):
    """HAEC cube topology: 3-dimensional hypercube

    Node index: s(x, y, z)
        x, y: Index in the same board
        z: The board index
    """

    ctl_prog = "ryu_cube_energy.py"

    def __init__(self, board_len=3, board_num=3, *args, **kwargs):
        self._board_len = board_len
        self._board_num = board_num

        self._intra_board_para = {
            "bw", 10,
            "delay", 0.1,
            "loss", 0
        }

        super(HAECCube, self).__init__(*args, **kwargs)
        logger.info(
            "[TOPO] HAECCube with board length: {} and board num: {} is built.".format(board_len, board_num))

    def build(self):
        self._build_one_board(0)

    def _build_one_board(self, board_idx):
        node_idx = 1
        for x in range(self._board_len):
            for y in range(self._board_len):
                hname, sname = [prefix + "{}{}{}".format(x, y, board_idx) for
                                prefix in ("h", "s")]
                self.addHost(hname,
                             ip="10.0.0.{}/24".format(node_idx),
                             ** self._host_kargs)
                self.addSwitch(sname,
                               dpid="0"*(DPID_LEN - 3)+"{}{}{}".format(x, y, board_idx))
                # Connect host and switch -> the port for host on the switch is
                # always 1. Important for routing!
                # self.addLink()
                node_idx += 1
