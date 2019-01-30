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

FRONTEND_URL = "http://192.168.0.100:8080"
BACKEND_URL = "http://192.168.0.102:8080"
BACKEND_IP = "192.168.0.102"
DEFAULT_MODE = "distributed"

MIGRATE_PERIOD = 5  # second
POST_PER_SECOND = 3

ENERGY_SCALE_FACTOR_CENTRAL = 1000
ENERGY_SCALE_FACTOR_DISTRIBUTED = 1000

last_valid_bw_central = 1
last_valid_bw_distributed = 1

SERVER_NUM = 3


def post_path(sender, receiver, path):
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


def post_state_global(consumption, max_temp):
    data = {
        "consumption": str(consumption),
        "maxTemperature": str(max_temp),
        "cpu": []
    }
    for _ in range(POST_PER_SECOND):
        requests.post(
            FRONTEND_URL + '/state/update',
            headers={"Content-type": "application/x-www-form-urlencoded"},
            data=json.dumps(data)
        )
    # print("POST global state: \n" + json.dumps(data))


def post_state_one_proc(proc_id, load, temp):
    data = {
        "id": str(proc_id),
        "load": str(load),
        "temperature": str(temp)
    }
    requests.post(
        FRONTEND_URL + '/state/update',
        headers={"Content-type": "application/x-www-form-urlencoded"},
        data=json.dumps(data)
    )
    print("POST state one proc: \n" + json.dumps(data))


def get_ip(name):
    return "10.{}.{}.{}".format(name[1], name[2], name[3])


def distributed_mode(topo, emu):
    print("# Run in distributed mode...")
    global last_valid_bw_distributed
    random.seed(time.time())
    srv_init_lst = list()  # A list of init server

    clt = "h{}{}{}".format(
        random.randint(1, 3), random.randint(1, 3),
        random.randint(1, 3)
    )

    while True:
        srv_init = "h{}{}{}".format(
            random.randint(1, 3), random.randint(1, 3),
            random.randint(1, 3)
        )
        if (srv_init[3] == clt[3]) or (srv_init in srv_init_lst):
            continue
        srv_init_lst.append((srv_init, get_ip(srv_init)))
        if len(srv_init_lst) == SERVER_NUM:
            break

    print("### client: {}, servers: {}".format(clt, ", ".join([x[0] for x in
                                                               srv_init_lst])))

    for srv, _ in srv_init_lst:
        # Update paths
        path = list(
            map(topo.get_proc_id, topo.get_migrate_dst_hops(clt, srv)))
        path = list(reversed(path))
        path.insert(0, topo.get_proc_id(clt))
        path.append(topo.get_proc_id(srv))
        post_path(
            topo.get_proc_id(clt), topo.get_proc_id(srv),

            path
        )
    for srv, srv_ip in srv_init_lst:
        srv_cmd = "iperf3 -s {} -D".format(srv_ip)
        clt_cmd = "iperf3 -c {} -u -t 60".format(srv_ip)
        emu.run_task_bg(srv, srv_cmd, None)
        emu.run_task_bg(clt, clt_cmd, None)

    for i in range(MIGRATE_PERIOD):
        bw = sum(emu.get_hosts_bw([clt])[clt])
        if bw == 0:
            bw = last_valid_bw_distributed
        else:
            last_valid_bw_distributed = bw

        energy = 0
        for srv, _ in srv_init_lst:
            energy += sum(
                [topo.get_link_energy_cost(clt, srv),
                 emu._query_power(clt), emu._query_power(srv)]
            )
        w_per_bit = (energy / bw) * 1000.0
        print("Energy per byte: {} mW/byte".format(w_per_bit))
        w_per_bit = w_per_bit / ENERGY_SCALE_FACTOR_DISTRIBUTED
        w_per_bit = min(w_per_bit, 10)
        post_state_global(w_per_bit, random.randint(50, 55))
        time.sleep(1)

    return clt, srv_init_lst


def centralized_mode(topo, emu, clt, srv_init, srv_init_ip):
    print("### Start centralized mode")
    global last_valid_bw_central
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

        for i in range(MIGRATE_PERIOD):
            bw = sum(emu.get_hosts_bw([clt])[clt])
            if bw == 0:
                bw = last_valid_bw_central
            else:
                last_valid_bw_central = bw
            energy = sum(
                [topo.get_link_energy_cost(clt, srv_cur),
                 emu._query_power(clt), emu._query_power(srv_cur)]
            )
            w_per_bit = (energy / bw) * 1000.0
            print("Energy per byte: {} mW/byte".format(w_per_bit))
            w_per_bit = w_per_bit / ENERGY_SCALE_FACTOR_CENTRAL
            w_per_bit = min(w_per_bit, 10)
            post_state_global(w_per_bit, random.randint(50, 55))
            time.sleep(1)


if __name__ == '__main__':

    loop_mode = True

    try:
        emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
        emu._url_create_flow = "put"
        emu._url_push_processor_info = "put"
        topo = HAECCube(
            host_type="process", board_len=3,
            intra_board_topo="mesh",
            link_energy_cost=(15.0, 15.0, 150)
        )
        exp_info = ExpInfo("hace_cube_link_energy", None,
                           topo, "process", None, None)

        emu.run_exp(exp_info)

        if loop_mode:
            print("# Run with loop mode")
            while True:
                clt, srv_init_lst = distributed_mode(topo, emu)
                time.sleep(MIGRATE_PERIOD)
                # centralized_mode(topo, emu, clt, srv_init, srv_init_ip)
                # time.sleep(MIGRATE_PERIOD)

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
