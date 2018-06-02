# -*- mode: ruby -*-
# vi: set ft=ruby :
# About: Vagrant file for the development environment

###############
#  Variables  #
###############

CPUS = 2
RAM = 2048

BOX = "bento/ubuntu-16.04"

####################
#  Vagrant Config  #
####################

Vagrant.configure("2") do |config|

    # --- MaxiNet Frontend ---
    config.vm.define "frontend" do |frontend|
        frontend.vm.box = BOX
        frontend.vm.hostname = "frontend"
        frontend.vm.provision :shell, path: "bootstrap.sh"

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
        worker.vm.provision :shell, path: "bootstrap.sh"

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
