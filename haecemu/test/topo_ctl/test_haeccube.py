#!/usr/bin/env python2

import time

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = HAECCube(host_type="docker", board_len=2)
    exp = emu.setup(topo)
    emu.ping_all()
    time.sleep(3)
    # emu.run_monitor()
    emu.print_docker_status()
    emu.print_host_ips()

    emu.wait()

finally:
    emu.cleanup()
