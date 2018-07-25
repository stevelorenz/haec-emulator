#! /usr/bin/env bash
#
# About: HAEC Emulator install script for Ubuntu
#

# Fail on error
set -e
set -o nounset

HAECEMU_DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../" && pwd -P )"
CONFIG_DIR="$HOME/.haecemu"

# Install dependencies
sudo apt-get install -y python2-pip
sudo apt-get install -y fabric

if [[ -d $CONFIG_DIR ]]; then
    echo "## WARN: Default config directory already exists. Remove it."
    rm -rf $CONFIG_DIR
fi

echo "## HAECEMU_DIR: $HAECEMU_DIR"

echo "## Install python lib."
cd $HAECEMU_DIR || exit
sudo python setup.py install

echo "## Install controller programs"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/controller"
echo "## Copy controller programs to $CONFIG_DIR/controller"
cp -r -T "$HAECEMU_DIR/controller" "$CONFIG_DIR/controller"

echo "## Copy HAECEMU config file"
cp -T "$HAECEMU_DIR/examples/config.json" "$CONFIG_DIR/config.json"

echo "# Installation finished."
