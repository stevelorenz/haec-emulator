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

import json
import math
from os.path import commonprefix
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

##############################
#  Helper Classes and Funcs  #
##############################


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


class TopolibError(Exception):
    pass


class _BTNode(object):
    """An individual node in a binary tree"""

    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None


class _BinaryTree(object):

    """Helper class for binary tree"""

    def __init__(self):
        pass

    def build(self, nodes, in_order=None, pre_order=None, post_order=None):
        """Build binary tree with given nodes and traversals"""

        if in_order and pre_order:
            pass

        elif pre_order and post_order:
            logger.warn("This only support for full binary tree")

        else:
            raise TopolibError("Invalid traversals for building a binary tree")

    def get_lca(self, n1, n2):
        pass

    def get_dist(self):
        pass


###################
#  Base Topology  #
###################

class BaseTopo(Topo):

    """Base topology class"""

    def __init__(self, host_type="process",
                 * args, **kwargs):
        if host_type not in HOST_TYPES:
            logger.error("Invalid host type, support host types {}".format(
                ", ".join(HOST_TYPES)))
            raise TopolibError
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

    def _update_dpid_table(self, dpid, sname):
        if dpid in self.dpid_table:
            raise TopolibError("Duplicated DPIDs")
        self.dpid_table[dpid] = sname

    def addLinkNamedIfce(self, src, dst, *args, **kwargs):
        """Add a link with named two interfaces"""
        self.addLink(src, dst,
                     intfName1="-".join((src, dst)),
                     intfName2="-".join((dst, src)),
                     * args, **kwargs
                     )

    def get_node_dist(self, src, dst):
        """Get the shortest distance between source and destination nodes

        :param src:
        :param dst:
        """
        raise NotImplementedError

    def get_link_energy_cost(self, src, dst):
        """Get the energy cost for the link(s) between source and destination
        nodes

        :param src:
        :param dst:
        """
        raise NotImplementedError

    def dumps(self, path):
        """Dump topology with JSON format"""
        # nodes
        # edges
        json.dumps([])


###################
#  Tree Topology  #
###################


class StaticPerfectFatTree(BaseTopo):
    """StaticPerfectFatTree"""

    # TODO: Use STP instead of learning switch
    ctl_prog = "ryu_l2_switch.py"

    def __init__(self, hosts, bwlimit=10, lat=0.1, link_energy_cost=5,
                 *args, **kwargs):
        """Simple fat tree topo with same link latency and bandwidth"""
        if not math.log(hosts, 2).is_integer():
            raise TopolibError(
                "StaticPerfectFatTree supports only perfect tree.")
        self._hosts = hosts
        self._depth = int(math.log(hosts, 2))
        self._b_fmt = "{0:0%sb}" % (self._depth + 1)

        self._bwlimit = bwlimit
        self._lat = lat
        self._link_energy_cost = link_energy_cost

        # Construct the helper binary tree
        # self._nodes_num = sum([2 ** l for l in range(self._depth + 1)])

        # self._pre_order = []
        # self._pre_order = ["s{}".format(x) for x in self._pre_order]

        # self._in_order = []
        # self._post_order = []
        # self._hlp_tree = _BinaryTree()

        super(StaticPerfectFatTree, self).__init__(*args, **kwargs)
        logger.info("[TOPO] StaticPerfectFatTree is built.")

    def _make_dpid(self, sname, idx):
        if idx > 250 or idx < 0:
            raise TopolibError("Invalid switch index.")
        dpid = "".join(("0" * (_DPID_LEN - len(str(idx))), str(idx)))
        self._update_dpid_table(dpid, sname)
        return dpid

    def get_depth(self):
        return self._depth

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
            self.addLinkNamedIfce(h, sw, bw=bw, delay=str(self._lat) + "ms")
            self.host_ifce_table[h] = "{}-{}".format(h, sw)
            tor.append(sw)

        toDo = tor  # nodes that have to be integrated into the tree

        # Add aggregation switches
        while len(toDo) > 1:
            newToDo = []
            for i in range(0, len(toDo), 2):  # binary tree
                sw = self.addSwitch("s" + str(s),
                                    dpid=self._make_dpid("s"+str(s), s),
                                    **dict(listenPort=(13000 + s - 1)))
                s = s + 1
                newToDo.append(sw)
                self.addLinkNamedIfce(toDo[i], sw, bw=bw,
                                      delay=str(self._lat) + "ms")
                if len(toDo) > (i + 1):
                    self.addLinkNamedIfce(toDo[i + 1], sw, bw=bw,
                                          delay=str(self._lat) + "ms")
            toDo = newToDo
            bw = 2.0 * bw

    def _get_lca(self, src, dst):
        """MARK: Temp solution"""
        cur = 0
        level_base = [0]
        for i in range(self._depth, 0, -1):
            cur = cur + 2**i
            level_base.append(cur)
        level_base = level_base[::-1]

        src_b = self._b_fmt.format(int(src[1:]) - 1)
        dst_b = self._b_fmt.format(int(dst[1:]) - 1)
        prefix = commonprefix((src_b, dst_b))
        lca = int(prefix, 2) + level_base[len(prefix) - 1] + 1
        return "{}{}".format(src[0], lca)

    def get_node_dist(self, src, dst):
        """
        Dist(n1, n2) = Dist(root, n1) + Dist(root, n2) - 2 * Dist(root, lca)
        MARK: Currently only support tor switches
        """
        lca = self._get_lca(src, dst)
        lca_b = self._b_fmt.format(int(lca[1:]) - 1)
        t = 0
        for c in lca_b:
            if c == "1":
                t += 1
            else:
                break
        dist = 2 * self._depth - 2*(self._depth - t)
        return dist

    def get_link_energy_cost(self, src, dst):
        dist = self.get_node_dist(src, dst)
        return dist * self._link_energy_cost

#######################
#  Hypecube Topology  #
#######################


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

    ctl_prog = "ryu_haeccube_dijkstra.py"

    INTRA_BOARD_TOPOS = ("dummy", "torus", "mesh")

    def __init__(self, board_len=3, board_num=3,
                 intra_board_topo="torus",
                 link_energy_cost=None,
                 * args, **kwargs):

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

        if not link_energy_cost:
            self.link_energy_cost = (5.0, 5.0, 25.0)
        else:
            self.link_energy_cost = link_energy_cost

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
    def _build_one_board(self, board_idx, topo):

        if topo not in self.INTRA_BOARD_TOPOS:
            logger.error("[HAECCube] Unknown topology to build a single board.")
            raise TopolibError
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
            for x in range(n):
                for y in range(n):
                    s = "s{}{}{}".format(x+1, y+1, board_idx+1)
                    if x == n - 1 and y == n - 1:
                        continue
                    elif y == n - 1:
                        neighbours = (
                            "s{}{}{}".format((x+1) + 1, y+1, board_idx+1),
                        )
                    elif x == n - 1:
                        neighbours = (
                            "s{}{}{}".format(x+1, (y+1)+1, board_idx+1),
                        )
                    else:
                        neighbours = (
                            "s{}{}{}".format(x+1, (y+1) + 1, board_idx+1),
                            "s{}{}{}".format((x+1) + 1, y+1, board_idx+1)
                        )
                    for nb in neighbours:
                            # Check if is a duplicated link
                        if (nb, s) not in self.links():
                            self.addLinkNamedIfce(
                                s, nb, ** self.intra_board_link_prop)

        elif topo == "dummy":
            pass

        return sws[:]

    def connect_boards(self, boards, mode="1to1"):
        if len(boards) == 1:
            raise TopolibError("Invalid board number.")
        logger.info("Connect boards with mode: %s", mode)
        boards = list(map(sorted, boards))
        for b_idx in range(0, len(boards) - 1):
            for s_a, s_b in zip(boards[b_idx], boards[b_idx + 1]):
                self.addLinkNamedIfce(s_a, s_b)

    def build(self):
        boards = [
            self._build_one_board(idx, self._intra_board_topo)
            for idx in range(0, 3)
        ]
        self.connect_boards(boards)

    def get_node_dist(self, src, dst):
        assert len(src) == len(dst)
        if self._intra_board_topo == "mesh":
            return [abs(int(c1) - int(c2)) for c1, c2 in zip(src[1:4], dst[1:4])]
        else:
            raise TopolibError("Not implemented yet")

    def get_link_energy_cost(self, src, dst):
        """Get the link energy cost between src and dst"""
        dists = self.get_node_dist(src, dst)
        return sum([d*c for d, c in zip(dists, self.link_energy_cost)])

    # MARK: Helper functions to cooperate with the Unity frontend
    def get_proc_id(self, sname):
        """Get the processor ID based on switch name"""
        proc_id = 0
        for idx, val in enumerate(sname[1:]):
            proc_id = proc_id + (int(val) - 1) * (self._board_len ** idx)
        proc_id = proc_id + 1

        return proc_id

    # TODO: Should be implemented in the SDN controller -> link energy depends
    # on the traffic state. Also migrate should support overlapping
    # --------------------------------------------------------------------------

    def get_migrate_dst_hops(self, src, dst):
        """Get hops to migrate the dst towards src"""
        assert len(src) == len(dst)
        hops = []
        s_il, d_il = (map(int, t) for t in (src[1:4], dst[1:4]))
        # z -> y -> x
        for idx in range(2, -1, -1):
            s, d = s_il[idx], d_il[idx]
            if d > s:
                while d > s:
                    d_il[idx] = d - 1
                    hops.append("h" + "".join(map(str, d_il)))
                    d = d - 1
            elif s > d:
                while d < s:
                    d_il[idx] = d + 1
                    hops.append("h" + "".join(map(str, d_il)))
                    d = d + 1
            else:
                pass
        return hops[:-1]
