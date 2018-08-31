#!/usr/bin/env python2
"""
About: Simple ping with HAECCube topology
"""

import time

from haecemu.emulator import Emulator, ExpInfo
from haecemu.topolib import StaticPerfectFatTree

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    tree = StaticPerfectFatTree(host_type="process", hosts=4,
                                link_energy_cost=5.0
                                )
    exp_info = ExpInfo("tree_link_energy", None,
                       tree, "process", None, None)
    emu.run_exp(exp_info)
    time.sleep(3)
    emu.cli()
    emu.wait()

finally:
    emu.stop_cur_exp()
    emu.cleanup()
