#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Show the energy per byte before and after the server migration
       For app, Iperf3 client and server are used.
"""

import json
import multiprocessing
import random
import sys
import time
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import requests

from haecemu.emulator import Emulator, ExpInfo
from haecemu.topolib import HAECCube

CUBE_LEN = 4  # number of nodes = (CUBE_LEN) ** 3

# MARK: Change NO_FRONDEND to False and change the FRONTEND_URL before running
# the demo, NO_FRONDEND is used for debugging and local testing
NO_FRONDEND = True
FRONTEND_URL = "http://192.168.0.100:8080"
BACKEND_URL = "http://192.168.0.102:8080"
BACKEND_IP = "192.168.0.102"
DEFAULT_MODE = "distributed"

MIGRATE_PERIOD = 2  # second
POST_PER_SECOND = 3

ENERGY_SCALE_FACTOR_CENTRAL = 1000
ENERGY_SCALE_FACTOR_DISTRIBUTED = 1000

last_valid_bw_central = 1
last_valid_bw_distributed = 1

idle_power_base = 1.5
work_power_base = 7


def post_path(sender, receiver, path):

    if NO_FRONDEND:
        return

    data = {
        "senderId": sender,
        "receiverId": receiver,
        "communicationPath": path
    }
    requests.post(
        FRONTEND_URL + '/path/update',
        headers={"Content-type": "application/x-www-form-urlencoded"},
        data=json.dumps(data)
    )
    # print("POST path: \n" + json.dumps(data))


def post_state_global(consumption, max_temp, proc_info_list=None):

    if NO_FRONDEND:
        return

    data = {
        "consumption": str(consumption),
        "maxTemperature": str(max_temp),
        "cpu": []
    }

    if proc_info_list:
        added_proc_list = [ x["id"] for x in proc_info_list ]
        for idx in range(1, 28):
            if idx not in added_proc_list:
                proc_info_list.append({"id": idx, "load": 0, "temperature":50})
        data["cpu"] = proc_info_list

    for _ in range(POST_PER_SECOND):
        requests.post(
            FRONTEND_URL + '/state/update',
            headers={"Content-type": "application/x-www-form-urlencoded"},
            data=json.dumps(data)
        )
    # print("POST global state: \n" + json.dumps(data))

def distributed_mode(topo, emu):
    print("### Start distributed mode")
    global last_valid_bw_distributed
    proc_info_list = list()

    random.seed(time.time())
    clt_board, srv_board = random.sample([1, CUBE_LEN], 2)
    clt_x, srv_x = random.sample([1, CUBE_LEN], 2)
    clt_y, srv_y = random.sample([1, CUBE_LEN], 2)
    clt = "h{}{}{}".format(clt_x, clt_y, clt_board)
    srv_init = "h{}{}{}".format(srv_x, srv_y, srv_board)
    srv_ip = "10.{}.{}.{}".format(srv_init[1], srv_init[2], srv_init[3])

    print("### Distributed mode: client: {}, server: {}".format(clt, srv_init))
    path = list(map(topo.get_proc_id, topo.get_migrate_dst_hops(clt, srv_init)))
    path = list(reversed(path))
    path.insert(0, topo.get_proc_id(clt))
    path.append(topo.get_proc_id(srv_init))
    post_path(
        topo.get_proc_id(clt), topo.get_proc_id(srv_init),
        path
    )

    for proc in path:
        proc_info_list.append({"id": proc, "load": 100, "temperature":50})

    srv_cmd = "iperf3 -s {} -D".format(srv_ip)
    clt_cmd = "iperf3 -c {} -u -t 60".format(srv_ip)
    emu.run_task_bg(srv_init, srv_cmd, None)
    emu.run_task_bg(clt, clt_cmd, None)

    for i in range(MIGRATE_PERIOD):
        bw = sum(emu.get_hosts_bw([clt])[clt])
        if bw == 0:
            bw = last_valid_bw_distributed
        else:
            last_valid_bw_distributed = bw

        proc_energy = len(path) * (work_power_base + random.random()) + (27 - len(path)) * (idle_power_base)
        energy = proc_energy + topo.get_link_energy_cost(clt, srv_init)
        print("Path len: {}, Proc energy: {}, energy: {}".format(len(path), proc_energy, energy))

        w_per_bit = (energy / bw) * 1000.0
        # print("Energy per byte: {} mW/byte".format(w_per_bit))
        w_per_bit = w_per_bit / ENERGY_SCALE_FACTOR_DISTRIBUTED
        w_per_bit = min(w_per_bit, 10)
        post_state_global(energy, random.randint(50, 55), proc_info_list)
        time.sleep(1)

    return clt, srv_init, srv_ip


def centralized_mode(topo, emu, clt, srv_init, srv_init_ip):
    print("### Start centralized mode")
    global last_valid_bw_central
    last_valid_bw_central = last_valid_bw_distributed

    hops = topo.get_migrate_dst_hops(clt, srv_init)
    print("### Selected migration hops: {}".format(json.dumps(hops)))

    for i in range(MIGRATE_PERIOD):
        time.sleep(1)

    srv_cur = srv_init

    for hop in hops:
        print("--- Migrate server from {} to {}. Namely from ID:{} to ID:{}".format(
            srv_cur, hop, topo.get_proc_id(srv_cur), topo.get_proc_id(hop)))

        srv_cmd = "iperf3 -s {} -D".format(srv_init_ip)
        clt_cmd = "iperf3 -c {} -u -t 60".format(srv_init_ip)
        emu.migrate_server(clt, srv_cur, hop, srv_cmd)
        emu.run_task_bg(clt, clt_cmd, None)
        print("---- After migration")
        srv_cur = hop
        # Update the path
        path = list(
            map(topo.get_proc_id, topo.get_migrate_dst_hops(clt, srv_cur)))
        path = list(reversed(path))
        path.insert(0, topo.get_proc_id(clt))
        path.append(topo.get_proc_id(srv_cur))
        post_path(
            topo.get_proc_id(clt), topo.get_proc_id(srv_cur),
            path
        )

        proc_info_list = list()
        for proc in path:
            proc_info_list.append({"id": proc, "load": 100, "temperature":50})

        for i in range(MIGRATE_PERIOD):
            bw = sum(emu.get_hosts_bw([clt])[clt])
            if bw == 0:
                bw = last_valid_bw_central
            else:
                last_valid_bw_central = bw

            proc_energy = len(path) * (work_power_base + random.random()) + (27 - len(path)) * (idle_power_base)
            energy = proc_energy + topo.get_link_energy_cost(clt, srv_cur)
            print("Path len: {}, Proc energy: {}, energy: {}".format(len(path), proc_energy, energy))

            w_per_bit = (energy / bw) * 1000.0
            #print("Energy per byte: {} mW/byte".format(w_per_bit))
            w_per_bit = w_per_bit / ENERGY_SCALE_FACTOR_CENTRAL
            w_per_bit = min(w_per_bit, 10)
            post_state_global(energy, random.randint(50, 55), proc_info_list)
            time.sleep(1)


if __name__ == '__main__':

    loop_mode = True

    try:
        emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
        emu._url_create_flow = "put"
        emu._url_push_processor_info = "put"
        topo = HAECCube(
            host_type="process", board_len=CUBE_LEN, board_num=CUBE_LEN,
            intra_board_topo="mesh",
            link_energy_cost=(
            2 * 112.5 / 1000.0 ,
            2 * 112.5 / 1000.0,
            2 * 2400 / 1000.0
            )
        )
        exp_info = ExpInfo("hace_cube_link_energy", None,
                           topo, "process", None, None)

        emu.run_exp(exp_info)

        if loop_mode:
            print("# Run with loop mode")
            while True:
                clt, srv_init, srv_init_ip = distributed_mode(topo, emu)
                time.sleep(3)
                centralized_mode(topo, emu, clt, srv_init, srv_init_ip)
                time.sleep(3)

        else:
            print("# Run with interactive mode")
            print("# WARN: Currently can not get the mode update request from the frontend")
            sys.exit(1)

            clt_init = None
            srv_init = None
            distral_proc = multiprocessing.Process(target=distributed_mode)
            central_proc = multiprocessing.Process(target=centralized_mode)

            # Start HTTP server
            class RequestHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write('Hello!')

                def do_POST(self):
                    print("Recv a POST request")
                    # TODO: Update mode

                httpd = HTTPServer(("", 80), RequestHandler)
                httpd.serve_forever()

    finally:
        emu.stop_cur_exp()
        emu.cleanup()
