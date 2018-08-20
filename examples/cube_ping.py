#!/usr/bin/env python2
"""
About: Simple ping with HAECCube topology
"""

import time

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = HAECCube(host_type="process", board_len=3,
                    intra_board_topo="mesh")
    exp = emu.setup(topo)
    emu.ping_all()
    time.sleep(3)
    emu.cli()
    emu.wait()

finally:
    emu.cleanup()
