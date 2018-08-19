#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Show the fantastic energy
"""

import time

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    topo = HAECCube(host_type="process", board_len=2,
                    intra_board_topo="mesh")
    exp = emu.setup(topo, run_ctl=True)

    emu.run_task_bg("h222", "iperf3 -s 10.2.2.2 -D", None)
    emu.run_task_bg("h111", "iperf3 -c 10.2.2.2 -u -t 60", None)
    for i in range(10):
        bw = sum(emu.get_hosts_bw(["h111"])["h111"])
        energy = sum(
            [topo.get_link_energy_cost("h111", "h222"),
             emu._query_power("h111"), emu._query_power("h222")]
        )
        w_per_bit = (energy / bw) * 1000.0
        print("Energy per byte: {} mW/byte".format(w_per_bit))
        time.sleep(1)

    emu.migrate_server("h111", "h222", "h121", "iperf3 -s 10.2.2.2 -D")
    emu.run_task_bg("h111", "iperf3 -c 10.2.2.2 -u -t 60", None)
    print("---- After migration")
    for i in range(10):
        bw = sum(emu.get_hosts_bw(["h111"])["h111"])
        energy = sum(
            [topo.get_link_energy_cost("h111", "h121"),
             emu._query_power("h111"), emu._query_power("h121")]
        )
        w_per_bit = (energy / bw) * 1000.0
        print("Energy per byte: {} mW/byte".format(w_per_bit))
        time.sleep(1)

    emu.cli()
    emu.wait()

finally:
    emu.cleanup()
