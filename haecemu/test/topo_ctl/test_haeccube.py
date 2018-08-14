#!/usr/bin/env python2

import time

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = HAECCube(host_type="docker", board_len=3)
    exp = emu.setup(topo)
    print("All hosts: %s".format(",".join(topo.hosts())))
    # emu.ping_all()
    time.sleep(3)
    # emu.run_monitor()
    emu.print_docker_status()

    emu.wait()

finally:
    emu.cleanup()
