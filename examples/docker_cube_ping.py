#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Test ping with Cube tology for containers
"""

from haecemu.manager import Manager
from haecemu.topolib import CubeTopo

if __name__ == '__main__':

    topo = CubeTopo()
    mgr = Manager()

    try:
        exp = mgr.setup(topo)
        print("# All hosts: ")
        print(topo.hosts())

        # First host ping all rest hosts
        h0 = topo.hosts()[0]
        print(exp.get_node(h0).cmd("ip addr"))

        for h in topo.hosts()[1:]:
            dst_node = exp.get_node(h)
            dst_ip = dst_node.IP()
            print("Destination IP: {}".format(dst_ip))
            print("Ping result:")
            print(exp.get_node(h0).cmd("ping -c 3 {}".format(dst_ip)))

    finally:
        mgr.cleanup()
