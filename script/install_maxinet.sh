#!/bin/bash
#
# About: Install MaxiNet with Containernet support

echo "MaxiNet 1.2 installer"
echo ""
echo "This program installs MaxiNet 1.2 and all requirements to the home directory of your user"

echo "Installing required dependencies."

sudo apt-get install -y git autoconf screen cmake build-essential sysstat python-matplotlib uuid-runtime

if [[ $1 = "-cn" ]]; then
    echo "Installing Containernet"
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
elif [[ $1 = "-mn" ]]; then
    echo "Installing Mininet"
    cd ~
    sudo rm -rf openflow &> /dev/null
    sudo rm -rf loxigen &> /dev/null
    sudo rm -rf pox &> /dev/null
    sudo rm -rf oftest &> /dev/null
    sudo rm -rf oflops &> /dev/null
    sudo rm -rf ryu &> /dev/null
    sudo rm -rf mininet &> /dev/null

    git clone https://github.com/mininet/mininet
    cd mininet
    git checkout -b 2.2.1rc1 2.2.1rc1
    cd util/
    ./install.sh

    # the mininet installer sometimes crashes with a zipimport.ZipImportError.
    # In that case, we retry installation.
    if [ "$?" != "0" ]
    then
        ./install.sh
    fi
else
    echo "Skip installing Mininet or Containernet"
fi


# Metis
if [[ $2 = "-mt" ]]; then
    echo "Installing Metis"
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
fi

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
