#! /bin/bash
#
# About: Install Ryu controller
#

HOME_DIR="$HOME"

sudo apt install -y gcc python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev
git clone https://github.com/osrg/ryu.git "$HOME_DIR/ryu"
cd "$HOME_DIR/ryu" || exit
pip install .
