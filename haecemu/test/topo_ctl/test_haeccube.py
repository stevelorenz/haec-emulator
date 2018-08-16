#!/usr/bin/env python2

import time

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = HAECCube(host_type="process", board_len=4)
    exp = emu.setup(topo, run_ctl=True)
    # emu.print_docker_status()
    # emu.ping_all()
    # emu.print_host_ips()
    emu.cli()

    emu.wait()

finally:
    emu.cleanup()
