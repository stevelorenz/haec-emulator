#!/bin/bash
#
# About: Install MaxiNet with Containernet support

echo "MaxiNet 1.2 installer"
echo ""
echo "This program installs MaxiNet 1.2 and all requirements to the home directory of your user"

echo "installing required dependencies."

sudo apt-get install -y git autoconf screen cmake build-essential sysstat python-matplotlib uuid-runtime

# Containernet
sudo apt-get install -y ansible aptitude
# Patch config file if necessary
grep "localhost ansible_connection=local" /etc/ansible/hosts >/dev/null
if [ $? -ne 0 ]; then
    echo "localhost ansible_connection=local" | sudo tee -a /etc/ansible/hosts
fi

cd ~
sudo rm -rf containernet &> /dev/null
sudo rm -rf oflops &> /dev/null
sudo rm -rf oftest &> /dev/null
sudo rm -rf openflow &> /dev/null
sudo rm -rf pox &> /dev/null
git clone https://github.com/containernet/containernet
cd containernet/ansible
sudo ansible-playbook install.yml

# Metis
cd ~
wget http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/metis-5.1.0.tar.gz
tar -xzf metis-5.1.0.tar.gz
rm metis-5.1.0.tar.gz
cd metis-5.1.0
make config
make
sudo make install
cd ~
rm -rf metis-5.1.0

# Pyro4
sudo apt-get install -y python-pip
sudo pip install Pyro4

# MaxiNet
cd ~
sudo rm -rf MaxiNet &> /dev/null
git clone https://github.com/MaxiNet/MaxiNet.git
cd MaxiNet
git checkout v1.2
sudo make install
