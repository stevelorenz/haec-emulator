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

from random import randint

from haecemu import log, util
from mininet.topo import Topo

logger = log.logger

try:
    from MaxiNet.Frontend.container import Docker
except ImportError:
    logger.info("[WARN] Can not import docker container for MaxiNet")

HOST_TYPES = ["process", "docker"]

# DPID is a 64 bit number, lower 48 bits for mac address, top 16 bits for
# implementer
_DPID_LEN = 16
_DPID_FMT = '%0{0}x'.format(_DPID_LEN)
DPID_PATTERN = r'[0-9a-f]{%d}' % _DPID_LEN


def dpid_to_str(dpid):
    return _DPID_FMT % dpid


def str_to_dpid(dpid_str):
    assert len(dpid_str) == _DPID_LEN
    return int(dpid_str, 16)


def rand_byte(max=255):
    return hex(randint(0, max))[2:]


def make_mac(idx):
    return "00:" + rand_byte() + ":" + \
        rand_byte() + ":00:00:" + hex(idx)[2:]


class HostWorker(object):

    def __init__(self, name, cost):
        self._name = name
        self._cost = cost


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

        self.name = ""
        self.dpid_table = {}  # map of switch name and DPIDs
        self.host_ifce_table = {}

        super(BaseTopo, self).__init__(*args, **kwargs)

        logger.debug("[TOPO] DPID table:")
        logger.debug(self.dpid_table)

    def addLinkNamedIfce(self, src, dst, *args, **kwargs):
        self.addLink(src, dst,
                     intfName1="-".join((src, dst)),
                     intfName2="-".join((dst, src)),
                     * args, **kwargs
                     )

    def _update_dpid_table(self, dpid, sname):
        if dpid in self.dpid_table:
            raise RuntimeError("Duplicated DPIDs")
        self.dpid_table[dpid] = sname

    def dumps(self):
        """Dump topology with JSON format"""
        # nodes
        # edges
        pass


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

    def _make_dpid(self, sname):
        pass

    def build(self):
        pass


class SimpleFatTree(BaseTopo):

    # TODO: Use STP instead of learning switch
    ctl_prog = "ryu_l2_switch.py"

    def __init__(self, hosts, bwlimit=10, lat=0.1, *args, **kwargs):
        """Simple fat tree topo with same link latency and bandwidth"""
        self._hosts = hosts
        self._bwlimit = bwlimit
        self._lat = lat
        super(SimpleFatTree, self).__init__(*args, **kwargs)
        logger.info("[TOPO] SimpleFatTree is built.")

    def _make_dpid(self, sname, idx):
        if idx > 250 or idx < 0:
            raise RuntimeError("Invalid switch index.")
        dpid = "".join(("0" * (_DPID_LEN - len(str(idx))), str(idx)))
        self._update_dpid_table(dpid, sname)
        return dpid

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
            sw = self.addSwitch("s" + str(s), dpid=self._make_dpid("s"+str(s), s),
                                **dict(listenPort=(13000 + s - 1)))
            s = s + 1
            self.addLink(h, sw, bw=bw, delay=str(self._lat) + "ms")
            tor.append(sw)
        toDo = tor  # nodes that have to be integrated into the tree
        while len(toDo) > 1:
            newToDo = []
            for i in range(0, len(toDo), 2):
                sw = self.addSwitch("s" + str(s),
                                    dpid=self._make_dpid("s"+str(s), s),
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

    Each node of the cube contains one switch and a host that is directly
    connected to the switch.

    Node index: s(x, y, z)
        x, y: Index in the same board
        z: The board index

    - Intra board nodes are statically connected.
    - Inter board nodes are dynamically connected by using MaxiNet experiment
    class.
    """

    # ctl_prog = "ryu_haeccube.py"
    ctl_prog = "ryu_haeccube_dijkstra.py"

    INTRA_BOARD_TOPOS = ("dummy", "torus", "mesh")

    def __init__(self, board_len=3, board_num=3,
                 intra_board_topo="torus",
                 *args, **kwargs):

        self.name = "haeccube"

        self._board_len = board_len
        self._board_num = board_num
        self._intra_board_topo = intra_board_topo

        self.intra_board_link_prop = {
            "bw": 10,
            "delay": 0.1,
            "loss": 0
        }

        # MARK: DEPEND on the node distance
        self.inter_board_link_prop = {
            "bw": 3,
            "delay": 0.5,
            "loss": 5
        }

        super(HAECCube, self).__init__(*args, **kwargs)
        logger.info(
            "[TOPO] HAECCube with board length: {} and board num: {} is built.".format(board_len, board_num))

    def _make_dpid(self, sname, x, y, board_idx):
        dpid = "".join((
            "0" * (_DPID_LEN - 4),
            "1{}{}{}".format(x, y, board_idx)
        ))
        self._update_dpid_table(dpid, sname)
        return dpid

    def _make_mac(self, x, y, board_idx):
        suffix = ":".join([hex(i)[2:] for i in (x, y, board_idx)])
        mac = ":".join(("00:00:00", suffix))
        return mac

    @util.print_time_func(logger.debug)
    def _build_one_board(self, board_idx, topo="torus"):

        if topo not in self.INTRA_BOARD_TOPOS:
            logger.error("[HAECCube] Unknown topology to build a single board.")
            raise RuntimeError
        logger.info(
            "[HAECCube] Topology used for intra-board connection: {}".format(topo))

        sws = list()
        n = self._board_len
        node_idx = 1
        for x in range(n):
            for y in range(n):
                hname, sname = [prefix + "{}{}{}".format(x+1, y+1, board_idx+1) for
                                prefix in ("h", "s")]
                self.addHost(hname,
                             ip="10.{}.{}.{}/8".format(x+1,
                                                       y+1, board_idx + 1),
                             mac=self._make_mac(x+1, y+1, board_idx + 1),
                             **self._host_kargs)
                sws.append(sname)
                self.addSwitch(sname,
                               # The DPID match the name of the switch
                               dpid=self._make_dpid(
                                   sname, x+1, y+1, board_idx+1),
                               ** dict(listenPort=(13000 + node_idx - 1))
                               )
                # Connect host and switch -> the port for host on the switch is
                # always 1. Important for routing!
                self.addLinkNamedIfce(
                    sname, hname, **self.intra_board_link_prop)
                self.host_ifce_table[hname] = "{}-{}".format(hname, sname)

                node_idx += 1

        if topo == "torus":
            for x in range(n):
                for y in range(n):
                    s = "s{}{}{}".format(x+1, y+1, board_idx+1)
                    neighbours = (
                        "s{}{}{}".format(x+1, (y+1) % n + 1, board_idx+1),
                        "s{}{}{}".format((x+1) % n + 1, y+1, board_idx+1)
                    )
                    for nb in neighbours:
                            # Check if is a duplicated link
                        if (nb, s) not in self.links():
                            self.addLinkNamedIfce(
                                s, nb, ** self.intra_board_link_prop)
        elif topo == "mesh":
            pass

        elif topo == "dummy":
            self.addLinkNamedIfce(
                "s111", "s121", **self.intra_board_link_prop
            )

        return sws[:]

    def connect_boards(self, boards, mode="1to1"):
        if len(boards) == 1:
            raise RuntimeError("Invalid board number.")
        logger.info("Connect boards with mode: %s", mode)
        boards = list(map(sorted, boards))
        for b_idx in range(0, len(boards) - 1):
            for s_a, s_b in zip(boards[b_idx], boards[b_idx + 1]):
                self.addLinkNamedIfce(s_a, s_b)

    def build(self):
        boards = [
            self._build_one_board(idx) for idx in range(0, 3)
        ]
        self.connect_boards(boards)
