#!/usr/bin/env python2
"""
About: A small example showing the usage of Docker containers.
"""

import time

from haecemu.manager import Manager
from mininet.topo import Topo
from MaxiNet.Frontend.container import Docker

# Use httpbin just for test
mgr = Manager(mode="test", remote_base_url="http://httpbin.org")
mgr._url_create_flow = "put"
mgr._url_push_processor_info = "put"


# Init test topology
topo = Topo()
p1 = topo.addHost("p1", cls=Docker, ip="10.0.0.251", dimage="ubuntu:trusty")
p2 = topo.addHost("p2", cls=Docker, ip="10.0.0.252", dimage="ubuntu:trusty")
s1 = topo.addSwitch("s1")
s2 = topo.addSwitch("s2")
topo.addLink(p1, s1)
topo.addLink(s1, s2)
topo.addLink(p2, s2)

try:
    exp = mgr.setup(topo)
    print("All processors: %s".format(",".join(topo.hosts())))

    print(exp.get_node("p1").cmd("ping -c 5 10.0.0.252"))
    mgr.create_flow(
        {'source': 'p1',
         'destination': 'p2',
         'duration': 3,
         'middle_nodes': [""]
         }
    )

    print(exp.get_node("p2").cmd("ping -c 5 10.0.0.251"))
    mgr.create_flow(
        {'source': 'p2',
         'destination': 'p1',
         'duration': 3,
         'middle_nodes': [""]
         }
    )
    time.sleep(1)
    mgr.push_processor("p1")
    time.sleep(3)

finally:
    mgr.cleanup()
