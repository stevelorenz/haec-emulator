#! /bin/bash
#
# add_maxinet_systemdunit.sh
#

SERVICE_FRONTEND="maxinet-frontend.service"
UNIT_FRONTEND="/etc/systemd/system/$SERVICE_FRONTEND"

SERVICE_WORKER="maxinet-worker.service"
UNIT_WORKER="/etc/systemd/system/$SERVICE_WORKER"

function print_help() {
    echo "Usage: $ bash add_maxinet_systemdunit.sh option user"
    echo "Options:"
    echo "    frontend: Add systemd unit for MaxiNet frontend server"
    echo "    worker: Add systemd unit for MaxiNet worker"

    echo ""
    echo "User: Given the user to start MaxiNet services"
    echo "INFO: MaxiNet.cfg should be placed in the home directory of this user"
    echo "      This user should also be allowed to run sudo without password"
}

if [[ "$#" -ne 2 ]]; then
    echo "Illegal number of parameters"
    print_help
    exit 1
fi

if [[ $1 == "frontend" ]]; then
    echo "# Add systemd unit for MaxiNet frontend server"
    if [[ -f "$UNIT_FRONTEND" ]]; then
        echo "# Unit file already exists."
    else
        sudo tee -a "$UNIT_FRONTEND" > /dev/null << EOL
[Unit]
Description=MaxiNet Frontend Server

[Service]
Type=simple
User=vagrant
ExecStart=/usr/local/bin/MaxiNetFrontendServer
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL
    fi
    sudo chmod 644 $UNIT_FRONTEND
    sudo systemctl daemon-reload
    sudo systemctl status $SERVICE_FRONTEND

    # MARK: Worker SHOULD run with sudo, but not directly uses root
    #       Because MaxiNet.cfg is in the user's home directory
elif [[ $1 == "worker" ]]; then
    echo "# Add systemd unit for MaxiNet worker server"

    if [[ -f "$UNIT_WORKER" ]]; then
        echo "# Unit file already exists."
    else
        sudo tee -a "$UNIT_WORKER" > /dev/null << EOL
[Unit]
Description=MaxiNet Worker Server

[Service]
Type=simple
User=vagrant
ExecStart=/usr/bin/sudo /usr/local/bin/MaxiNetWorker
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL
    fi
    sudo chmod 644 $UNIT_WORKER
    sudo systemctl daemon-reload
    sudo systemctl status $SERVICE_WORKER

else
    echo "[ERROR] Unknown option."
    echo ""
    print_help
    exit 1
fi
