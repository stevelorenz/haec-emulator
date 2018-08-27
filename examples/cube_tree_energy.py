#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Comparison of energy between HAECCube and Tree topology
"""

import random
import time

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube, SimpleFatTree

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

# Run Fattree
try:
    tree = SimpleFatTree(host_type="process", hosts=4)
    exp = emu.setup(tree, run_ctl=True)
    emu.cli()

finally:
    emu.cleanup()

time.sleep(10)

# Run HAECCube
try:
    cube = HAECCube(
        host_type="process", board_len=3,
        intra_board_topo="mesh",
        link_energy_cost=(5.0, 5.0, 20.0)
    )
    exp = emu.setup(cube, run_ctl=True)
    emu.cli()
    emu.wait()

finally:
    emu.cleanup()


# Compare the energy per bytes
