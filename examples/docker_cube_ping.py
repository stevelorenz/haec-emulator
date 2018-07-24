#!/usr/bin/env python2
"""
About: Simple ping with Cube topology
"""

import time

from haecemu.emulator import Emulator
from haecemu.topolib import CubeTopo

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = CubeTopo()
    exp = emu.setup(topo)
    print("All hosts: %s".format(",".join(topo.hosts())))
    emu.ping_all()
    time.sleep(3)
    emu.run_monitor()

finally:
    emu.cleanup()
