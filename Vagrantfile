# -*- mode: ruby -*-
# vi: set ft=ruby :
# About: Vagrant file for the development environment

###############
#  Variables  #
###############

CPUS = 2
RAM = 2048

BOX = "bento/ubuntu-16.04"

######################
#  Provision Script  #
######################

# Common bootstrap
$bootstrap= <<-SCRIPT
# Install dependencies
sudo apt update
sudo apt install -y git pkg-config gdb
sudo apt install -y bash-completion htop dfc
sudo apt install -y iperf iperf3
sudo apt install -y python-pip
# Add termite infos
wget https://raw.githubusercontent.com/thestinger/termite/master/termite.terminfo -O /home/vagrant/termite.terminfo
tic -x /home/vagrant/termite.terminfo
# Get zuo's dotfiles
git clone https://github.com/stevelorenz/dotfiles.git /home/vagrant/dotfiles
cp /home/vagrant/dotfiles/tmux/tmux.conf /home/vagrant/.tmux.conf
SCRIPT

$install_ryu= <<-SCRIPT
sudo apt install -y gcc python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev
git clone git://github.com/osrg/ryu.git /home/vagrant/ryu
cd /home/vagrant/ryu
pip install .
SCRIPT

####################
#  Vagrant Config  #
####################

Vagrant.configure("2") do |config|

  # --- MaxiNet Frontend ---
  config.vm.define "frontend" do |frontend|
    frontend.vm.box = BOX
    frontend.vm.hostname = "frontend"
    frontend.vm.provision :shell, inline: $bootstrap
    frontend.vm.provision :shell, inline: $install_ryu
    frontend.vm.network "private_network", ip: "10.0.1.11"

    # VirtualBox-specific configuration
    frontend.vm.provider "virtualbox" do |vb|
      vb.name = "ubuntu-16.04-frontend"
      vb.memory = RAM
      vb.cpus = CPUS
      # MARK: The CPU should enable SSE3 or SSE4 to compile DPDK
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
    end
  end

  config.vm.define "worker" do |worker|
    worker.vm.box = BOX
    worker.vm.hostname = "worker"
    worker.vm.provision :shell, inline: $bootstrap
    worker.vm.network "private_network", ip: "10.0.1.12"

    # VirtualBox-specific configuration
    worker.vm.provider "virtualbox" do |vb|
      vb.name = "ubuntu-16.04-worker"
      vb.memory = RAM
      vb.cpus = CPUS
      # MARK: The CPU should enable SSE3 or SSE4 to compile DPDK
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
      vb.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
    end
  end

end
