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
from haecemu.topolib import HAECCube, StaticPerfectFatTree

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

# Run Fattree
try:
    tree = StaticPerfectFatTree(host_type="process", hosts=32)
    exp = emu.setup(tree, run_ctl=True)
    emu.cli()

finally:
    emu.cleanup()

time.sleep(3)
