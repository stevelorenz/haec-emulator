#!/usr/bin/env python2

import time
import random

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = HAECCube(host_type="process", board_len=2,
                    intra_board_topo="mesh"
                    )
    exp = emu.setup(topo, run_ctl=True)
    emu.swap_ips_random(10)

    # Test bw monitor
    emu.run_iperf_daemon(topo.hosts())
    for _ in range(2):
        src, dst = random.sample(topo.hosts(), 2)
        print(
            "[TEST] Run Iperf UDP traffic, SRC: {}, DST, {}, Dist: {}".format(
                src, dst, topo.get_node_dist(src, dst))
        )
        emu.run_iperf_udp(src, dst)
    for i in range(10):
        bw = emu.get_hosts_bw(sorted(topo.hosts())[:])
        print(bw)
        time.sleep(1)
    emu.kill_iperf_daemon(topo.hosts())

    emu.cli()
    emu.wait()

finally:
    emu.cleanup()
