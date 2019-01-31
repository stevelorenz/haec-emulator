#! /bin/bash
#
# About: Run iperfs on two Odroids in a loop
#

ODROID_P3_N2="192.168.1.106"
ODROID_P3_N14="192.168.1.113"

if [[ "$1" == "run" ]]; then
    echo "Run Iperf traffic generator"
    ssh "odroid@$ODROID_P3_N2" nohup /home/odroid/run_iperf_server.sh &
    ssh "odroid@$ODROID_P3_N14" nohup /home/odroid/run_iperf_server.sh &

    sleep 3

    ssh "odroid@$ODROID_P3_N2" nohup /home/odroid/run_iperf_client.sh &
    ssh "odroid@$ODROID_P3_N14" nohup /home/odroid/run_iperf_client.sh &

elif [[ "$1" == "stop" ]]; then
    echo "Stop iperf traffic generator"
    ssh "odroid@$ODROID_P3_N2" killall iperf3
    ssh "odroid@$ODROID_P3_N2" killall nohup
    ssh "odroid@$ODROID_P3_N2" killall run_iperf_client.sh
    ssh "odroid@$ODROID_P3_N2" killall run_iperf_server.sh

    ssh "odroid@$ODROID_P3_N14" killall iperf3
    ssh "odroid@$ODROID_P3_N14" killall nohup
    ssh "odroid@$ODROID_P3_N14" killall run_iperf_client.sh
    ssh "odroid@$ODROID_P3_N14" killall run_iperf_server.sh

elif [[ "$1" == "net" ]]; then
    echo "Restarting the networking service on Odroids"
    ssh "odroid@$ODROID_P3_N2" sudo systemctl restart networking.service
    ssh "odroid@$ODROID_P3_N14" sudo systemctl restart networking.service

else
    echo "Usage: bash ./iperf_loop.sh [run, stop, net]"
fi

