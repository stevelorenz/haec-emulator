#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Comparison of energy between HAECCube and StaticPerfectFatTree topology
"""

import random
import time

from haecemu.emulator import Emulator, ExpInfo
from haecemu.topolib import HAECCube, StaticPerfectFatTree


def random_cs_energy_test(emu, topo, round_num=5):
    energy_per_byte = list()
    for r in range(round_num):
        clt, srv = random.sample(topo.hosts(), 2)
        print("# Round {}, client: {}, server: {}".format(r+1, clt, srv))
        # MARK: Temp solution here, _var SHOULD not be used.
        srv_ip = emu._cur_exp.get_node(srv).IP()
        srv_cmd = "iperf3 -s {} -D".format(srv_ip)
        clt_cmd = "iperf3 -c {} -u -t 60".format(srv_ip)

        emu.run_task_bg(srv, srv_cmd, None)
        emu.run_task_bg(clt, clt_cmd, None)
        time.sleep(3)
        bw = sum(emu.get_hosts_bw([clt])[clt])
        energy = sum(
            [topo.get_link_energy_cost(clt, srv),
             emu._query_power(clt), emu._query_power(srv)]
        )
        w_per_bit = (energy / bw) * 1000.0
        energy_per_byte.append(w_per_bit)
        time.sleep(1)

    return energy_per_byte


# Use httpbin just for test HTTP requests
emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

print("####### Run StaticPerfectFatTree experiment")
try:
    tree = StaticPerfectFatTree(host_type="process", hosts=32,
                                link_energy_cost=5.0
                                )
    exp_info = ExpInfo("tree_link_energy", None,
                       tree, "process", None, None)
    emu.run_exp(exp_info)
    result = random_cs_energy_test(emu, tree)
    tree_avg = sum(result) / len(result)
    print("[FatTree] Average energy consumption: {} mW/byte.".format(tree_avg))

finally:
    emu.stop_cur_exp()
    emu.cleanup()

time.sleep(3)

print("####### Run HAECCube experiment")
try:
    cube = HAECCube(
        host_type="process", board_len=3,
        intra_board_topo="mesh",
        link_energy_cost=(5.0, 5.0, 5.0)
    )

    exp_info = ExpInfo("hace_cube_ping", None, cube, "process", None, None)
    emu.run_exp(exp_info)
    result = random_cs_energy_test(emu, cube)
    cube_avg = sum(result) / len(result)
    print("[Cube] Average energy consumption: {} mW/byte.".format(cube_avg))
    emu.wait()

finally:
    emu.stop_cur_exp()
    emu.cleanup()

print("Summary: AEC of fattree: {}, of HAECCube: {} mW/byte".format(tree_avg,
                                                                    cube_avg))
print("The gain of HAECCube: {} %%".format(
    (tree_avg - cube_avg) / tree_avg * 100.0
))
