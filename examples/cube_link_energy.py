#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Show the energy per byte before and after the server migration
       For app, Iperf3 client and server are used.
"""

import json
import time
import random

from haecemu.emulator import Emulator
from haecemu.topolib import HAECCube

# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

CHART_FRONT_URL = "http://127.0.0.1:8000/energy_per_byte"

try:
    topo = HAECCube(
        host_type="process", board_len=3,
        intra_board_topo="mesh",
        link_energy_cost=(5.0, 5.0, 20.0)
    )

    exp = emu.setup(topo, run_ctl=True)

    migrate_period = 5  # second

    clt, srv_cur = random.sample(topo.hosts(), 2)
    srv_ip = "10.{}.{}.{}".format(srv_cur[1], srv_cur[2], srv_cur[3])
    print("### Initial state: client: {}, server: {}".format(clt, srv_cur))

    srv_cmd = "iperf3 -s {} -D".format(srv_ip)
    clt_cmd = "iperf3 -c {} -u -t 60".format(srv_ip)
    hops = topo.get_migrate_dst_hops(clt, srv_cur)
    print("### Selected migration hops: {}".format(json.dumps(hops)))

    emu.run_task_bg(srv_cur, srv_cmd, None)
    emu.run_task_bg(clt, clt_cmd, None)

    for i in range(migrate_period):
        bw = sum(emu.get_hosts_bw([clt])[clt])
        energy = sum(
            [topo.get_link_energy_cost(clt, srv_cur),
             emu._query_power(clt), emu._query_power(srv_cur)]
        )
        w_per_bit = (energy / bw) * 1000.0
        print("Energy per byte: {} mW/byte".format(w_per_bit))
        time.sleep(1)

    for hop in hops:
        print("--- Migrate server from {} to {}".format(srv_cur, hop))
        emu.migrate_server(clt, srv_cur, hop, srv_cmd)
        emu.run_task_bg(clt, clt_cmd, None)
        print("---- After migration")
        for i in range(migrate_period):
            bw = sum(emu.get_hosts_bw([clt])[clt])
            energy = sum(
                [topo.get_link_energy_cost(clt, hop),
                 emu._query_power(clt), emu._query_power(hop)]
            )
            w_per_bit = (energy / bw) * 1000.0
            print("Energy per byte: {} mW/byte".format(w_per_bit))
            time.sleep(1)
        srv_cur = hop

    emu.cli()
    emu.wait()

finally:
    emu.cleanup()
