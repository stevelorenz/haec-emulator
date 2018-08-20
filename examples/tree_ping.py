#!/usr/bin/env python2
"""
About: Simple ping with FatTree topology
"""

import time

from haecemu.emulator import Emulator
from haecemu.topolib import SimpleFatTree

# Use httpbin just for test HTTP requests
emu = Emulator(mode="emu", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    # Use docker for each host, alternative: host_type="process"
    topo = SimpleFatTree(hosts=2, host_type="docker")
    exp = emu.setup(topo)
    emu.ping_all()
    emu.cli()
    emu.wait()

finally:
    emu.cleanup()
