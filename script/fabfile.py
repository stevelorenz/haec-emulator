#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#


"""
About: Manage HAEC emualator on HAEC playground with fabric

 MARK:
    - Use fabric 1
"""

from __future__ import with_statement

from re import search
from time import sleep, strftime

from fabric.api import (cd, env, get, local, parallel, put, run, settings,
                        sudo, task)
from fabric.context_managers import hide
from fabric.contrib import project

BLACK_LIST = ["10.0.1.1", "10.0.1.11"]

# number of times for connection
env.connection_attempts = 1
# skip the unavailable hosts
env.skip_bad_hosts = True
env.colorize_errrors = True

WORKER_ROLE_FILE = "./workers.txt"
WORKER_USER = "odroid"
SSH_PORT = "22"

with open("./workers.txt", "r") as f:
    WORKERS = f.readlines()
    if not WORKERS:
        raise RuntimeError("No available workers.")

VM_WOKERS = ["vagrant@10.0.1.12:22"]

env.roledefs = {
    "workers": WORKERS,
    "vm_workers": VM_WOKERS
}

if not env.roles and not env.hosts:
    env.roles = ['workers']

# set password directory
PASSWORD_DICT = {}
for worker in WORKERS:
    PASSWORD_DICT[worker] = "odroid"

for vm_worker in VM_WOKERS:
    PASSWORD_DICT[vm_worker] = "vagrant"

env.passwords = PASSWORD_DICT


@task
def get_workers(network=""):
    """Scan workers in the network and output results in workers.txt"""
    scan_result = local("sudo nmap -n -sn -PS22 " + network +
                        " | awk '/^Nmap scan/ {print $5}'", capture=True)
    ips = scan_result.stdout.splitlines()
    ips = [x for x in ips if x not in BLACK_LIST]
    if ips:
        print("IP of available workers: ")
        print(", ".join(ips))
        workers = [
            WORKER_USER + "@" + ip + ":" + SSH_PORT
            for ip in ips
        ]
        print("Store workers in workers.txt file")
        with open("./workers.txt", "w+") as f:
            f.writelines(workers)

    else:
        print("No available workers.")


@task
def get_links():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        ret = run("sudo ip -o addr")
        for line in ret.splitlines():
            print(line)


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
    with settings(hide('warnings'), warn_only=True):
        count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])
        while count == 0:
            sudo('nohup MaxiNetWorker > /dev/null 2>&1 &', pty=False)
            sleep(1)
            count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])


@task
@parallel
def kill_worker():
    with settings(hide('warnings'), warn_only=True):
        count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])
        while count > 0:
            sudo('killall MaxiNetWorker', pty=False)
            sleep(1)
            count = int(run('pgrep -c MaxiNetWorker').splitlines()[0])


def gen_mxn_config():
    """Generate MaxiNet config file."""
    pass


def install_mxn():
    """Install MaxiNet on workers"""
    pass


@task
@parallel
def put_mxn_cfg(local_path=""):
    """Put MaxiNet config file."""
    remote_path = '~/.MaxiNet.cfg'
    put(local_path, remote_path)
