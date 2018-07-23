#! /bin/bash
#
# About: Run HAEC emulator
#
#

if [[ $1 = "-f" ]]; then
    echo "Run MaxiNet frontend server"
    sudo MaxiNetFrontendServer
elif [[ $1 = "-w" ]]; then
    echo "Run MaxiNet Worker"
    sudo MaxiNetWorker
fi
