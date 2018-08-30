#!/usr/bin/env python2

from haecemu.emulator import Emulator
from haecemu.topolib import StaticPerfectFatTree

emu = Emulator(mode="test", remote_base_url="http://httpbin.org")
emu._url_create_flow = "put"
emu._url_push_processor_info = "put"

try:
    # topo = StaticPerfectFatTree(hosts=2, host_type="docker")
    topo = StaticPerfectFatTree(hosts=32, host_type="process")
    exp = emu.setup(topo)
    emu.print_docker_status()

    emu.cli()
    emu.wait()

except Exception as e:
    print(e)

finally:
    emu.cleanup()
