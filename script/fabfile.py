#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Manage HAEC emulator on HAEC playground with fabric

MARK:
    - All operations are written in a single fabfile

        - By default, tasks are executed on every host in the ./workers.txt

        - Tasks for control host are decorated with @hosts("odroid@localhost")
            e.g. fab get_workers: Use nmap to scan all active workers in the LAN
            and export them into ./workers.txt. This runs only on the control
            node.

    - Use fabric 1. TODO: Move to fabric 2

Email: xianglinks@gmail.com
"""

from __future__ import with_statement

from re import search
from time import sleep, strftime

from fabric.api import (cd, env, get, local, parallel, put, run, settings, sudo,
                        task, execute)
from fabric.context_managers import hide
from fabric.contrib import project
from fabric.contrib import files
from fabric.contrib.files import contains, append, comment
from fabric import decorators

BLACK_LIST = [
    "10.0.1.1", "10.0.1.11", "192.168.0.1", "192.168.0.2", "192.168.0.100",
    "192.168.0.101", "192.168.0.102"
]

# number of times for connection
env.connection_attempts = 1
# skip the unavailable hosts
env.skip_bad_hosts = True
env.colorize_errrors = True

WORKER_ROLE_FILE = "./workers.txt"
WORKER_USER = "odroid"
SSH_PORT = "22"

with open("./workers.txt", "r") as f:
    WORKERS = [w.strip() for w in f.readlines()]
    if not WORKERS:
        print("[WARN] No workers in the workers.txt")
        print("Run get_workers to get available worker info.")

VM_WOKERS = ["vagrant@10.0.1.12:22"]

env.roledefs = {"workers": WORKERS, "vm_workers": VM_WOKERS}

# set default role and hosts
if not env.roles and not env.hosts:
    env.roles = ['workers']
    env.hosts = WORKERS

# set password directory
PASSWORD_DICT = {}
for worker in WORKERS:
    PASSWORD_DICT[worker] = "odroid"

for vm_worker in VM_WOKERS:
    PASSWORD_DICT[vm_worker] = "vagrant"

env.passwords = PASSWORD_DICT


@task
@decorators.hosts(['odroid@localhost'])
def get_workers(network=""):
    """Scan workers in the network and output results in workers.txt"""
    scan_result = local(
        "sudo nmap -n -sn -PS22 " + network +
        " | awk '/^Nmap scan/ {print $5}'",
        capture=True)
    ips = scan_result.stdout.splitlines()
    ips = [x for x in ips if x not in BLACK_LIST]
    if ips:
        print("IP of available workers: ")
        print(", ".join(ips))
        workers = [WORKER_USER + "@" + ip + ":" + SSH_PORT for ip in ips]
        print("Store workers in workers.txt file")
        with open("./workers.txt", "w+") as f:
            for worker in workers:
                f.write("{}\n".format(worker))

    else:
        print("No available workers.")


@task
def get_links():
    with settings(hide('warnings', 'running', 'stdout', 'stderr')):
        ret = run("sudo ip -o addr")
        for line in ret.splitlines():
            print(line)


def _install_pkgs(pkgs):
    for pkg in pkgs:
        sudo("apt-get install -y {}".format(pkg))


@task
def run_frontend():
    local("MaxiNetFrontendServer > /dev/null 2>&1 &")
    sleep(3)
    local("MaxiNetStatus")


@task
def kill_frontend():
    local("sudo killall MaxiNetFrontendServer")


@task
def run_worker():
    with settings(hide('warnings')):
        count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])
        while count == 0:
            sudo('nohup MaxiNetWorker > /dev/null 2>&1 &', pty=False)
            sleep(1)
            count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])


@task
@parallel
def kill_worker():
    with settings(hide('warnings')):
        count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])
        while count > 0:
            sudo('killall MaxiNetWorker', pty=False)
            sleep(1)
            count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])


def _get_hostname():
    hostname = run("cat /etc/hostname")
    return hostname

@task
@decorators.hosts("odroid@localhost")
def gen_mxn_config():
    """ Generate MaxiNet config file

    Worker item:
    [host_name]
    ip = XXX
    share = XXX
    """
    tpl_opts = {"controller_ip": "192.168.0.102"}
    """Generate MaxiNet config file."""
    template = """
; About: MaxiNet configuration for local tests.
; place this at ~/.MaxiNet.cfg

[all]
; Password used by worker to authenticate themselves to the FrontendServer
password = HAECEMU
controller = {controller_ip}
logLevel = INFO        ; Either CRITICAL, ERROR, WARNING, INFO  or DEBUG
port_ns = 9090         ; Nameserver port
port_sshd = 5345       ; Port where MaxiNet will start an ssh server on each worker
runWith1500MTU = True  ; Set this to True if your physical network can not handle MTUs >1500.
useMultipleIPs = 0     ; for RSS load balancing. Set to n > 0 to use multiple IP addresses per worker. More information on this feature can be found at MaxiNets github Wiki.
deactivateTSO = True   ; Deactivate TCP-Segmentation-Offloading at the emulated hosts.
sshuser = odroid       ; On Debian set this to root. On ubuntu set this to user which can do passwordless sudo
usesudo = True         ; If sshuser is set to something different than root set this to True.

; Frontend
[FrontendServer]
ip = {controller_ip}
threadpool = 64
    """.format(**tpl_opts)

    worker_item = """
[{host_name}]
ip={ip}
share={share}
    """
    worker_items = []
    with settings(hide('warnings', 'running', 'stdout')):
        ret = execute(_get_hostname, hosts=env.hosts)
    for host in env.hosts:
        worker_items.append(worker_item.format(**{
            "host_name": ret[host],
            "ip": host.split("@")[1][:-3],
            "share": "1"
            })
        )
    workers = '\n'.join(worker_items)
    cfg = '\n'.join([template, workers])
    with open("./MaxiNet.cfg", "w+") as cfg_file:
        cfg_file.write(cfg)


@parallel
def get_workers_with_hostname():
    """Get workers with hostnames used to generate mxn config"""
    pass


@task
def install_mxn(mn_type="mininet"):
    """Install MaxiNet on workers"""
    with settings(hide('warnings', 'running')):
        run("git clone https://github.com/stevelorenz/haec-emulator.git ~/haec-emulator"
            )
        run("bash ~/haec-emualator/script/install_maxinet.sh")


@task
@parallel
def put_mxn_cfg(local_path="./MaxiNet.cfg"):
    """Put MaxiNet config file."""
    remote_path = '~/.MaxiNet.cfg'
    put(local_path, remote_path)


@task
# @parallel
def setup_mxn_worker():
    """Setup MaxiNet worker on the Odroid

    Containernet, MaxiNet should be installed on each worker odroid.
    """

    with settings(hide('warnings')):
        # with settings(hide('warnings', 'running','stdout','stderr')):
        print("OVS status")
        print(sudo("ovs-vsctl show"))
        cmd = []
        if files.exists('/etc/sudoers.d/odroid'):
            print("User odroid is already configured for sudo")
        else:
            sudo(
                "echo \"odroid ALL=(ALL) NOPASSWD:ALL\" | tee /etc/sudoers.d/odroid"
            )
        if not files.exists('~/containernet'):
            sudo("apt-get update")
            sudo("apt-get install -y git")
            cmd = []
            cmd.append(
                "git clone https://github.com/containernet/containernet.git ~/containernet"
            )
            cmd.append(
                "sed -i -e 's/amd64/armhf/g' ~/containernet/ansible/install.yml"
            )
            cmd.append(
                "sed -i -e 's/iproute/iproute2/g' ~/containernet/util/install.sh"
            )
            cmd.append("cd ~/containernet/ansible/")
            cmd.append(
                "sudo ansible-playbook -i \"localhost,\" -c local install.yml")
            run("\n".join(cmd))
        else:
            print("Containernet is already installed. Output of 'sudo mn -c'.")
            ret = sudo("mn -c")
            print(ret)

        if not files.exists("~/MaxiNet"):
            put("./install_maxinet.sh", "~/install_maxinet.sh")
            run("bash ~/install_maxinet.sh -nn")
        else:
            print("MaxiNet is already installed. Output of MaxiNet worker")
            print(sudo("MaxiNetWorker"))


@task
def cleanup_ovs():
    cmd = """
for bridge in `ovs-vsctl list-br`; do
ovs-vsctl del-br $bridge
done
    """
    with settings(hide('warnings', 'running', 'stderr')):
        sudo(cmd)
        sudo("ovs-vsctl show")


@task
def check_mxn_status():
    """Check MaxiNet Status"""
    with settings(hide('warnings', 'running', 'stdout')):
        print("# Check MaxiNetWorker proc")
        print(sudo("ps aux | grep [M]axiNetWorker"))

        print("# Check running containers")
        print(sudo("docker container ls"))
