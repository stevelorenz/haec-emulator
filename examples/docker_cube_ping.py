#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Test ping with Cube topology with Docker containers
"""

from haecemu.manager import Manager
from haecemu.topolib import CubeTopo

if __name__ == '__main__':

    topo = CubeTopo()
    mgr = Manager()

    try:
        exp = mgr.setup(topo)
        print("# All processors: ")
        print(topo.hosts())

        # First host ping all rest hosts
        p0 = topo.hosts()[0]
        print(exp.get_node(p0).cmd("ip addr"))

        for p in topo.hosts()[1:]:
            dst_p_node = exp.get_node(p)
            dst_ip = dst_p_node.IP()
            print("Destination Processor IP: {}".format(dst_ip))
            print("Ping result:")
            print(exp.get_node(p0).cmd("ping -c 3 {}".format(dst_ip)))

    finally:
        mgr.cleanup()
