#!/usr/bin/env python2
"""
About: Simple ping with HAECCube topology
"""

import time
import sys

from haecemu.emulator import Emulator, ExpInfo
from haecemu.topolib import HAECCube

if __name__ == "__main__":

    if len(sys.argv) == 1:
        board_len = 3
    else:
        board_len = int(sys.argv[1])

    # Use httpbin just for test HTTP requests
    emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
    emu._url_create_flow = "put"
    emu._url_push_processor_info = "put"

    try:
        topo = HAECCube(host_type="process", board_len=board_len,
                        intra_board_topo="mesh")

        exp_info = ExpInfo("hace_cube_ping", None, topo, "process", None, None)
        emu.run_exp(exp_info)
        emu.ping_all()
        time.sleep(3)
        emu.cli()
        emu.wait()

    finally:
        emu.stop_cur_exp()
        emu.cleanup()
