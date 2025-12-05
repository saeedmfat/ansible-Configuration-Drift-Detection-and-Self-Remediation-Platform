Vagrant.configure("2") do |config|
  # Control VM (Ansible Controller + Git Server + Reporting)
  config.vm.define "control" do |control|
    control.vm.box = "ubuntu/focal64"
    control.vm.hostname = "control"
    control.vm.network "private_network", ip: "192.168.60.10"
    control.vm.provider "virtualbox" do |vb|
      vb.memory = "2048"
      vb.cpus = 2
      vb.name = "config-drift-control"
    end
  end

  # Target 1 - Ubuntu
  config.vm.define "target1" do |target1|
    target1.vm.box = "ubuntu/focal64"
    target1.vm.hostname = "target1"
    target1.vm.network "private_network", ip: "192.168.60.11"
    target1.vm.provider "virtualbox" do |vb|
      vb.memory = "2048"
      vb.cpus = 1
      vb.name = "config-drift-target1"
    end
  end

  # Target 2 - Ubuntu
  config.vm.define "target2" do |target2|
    target2.vm.box = "ubuntu/focal64"
    target2.vm.hostname = "target2"
    target2.vm.network "private_network", ip: "192.168.60.12"
    target2.vm.provider "virtualbox" do |vb|
      vb.memory = "2048"
      vb.cpus = 1
      vb.name = "config-drift-target2"
    end
  end

  # Target 3 - Rocky Linux (CentOS alternative)
  config.vm.define "target3" do |target3|
    target3.vm.box = "rockylinux/8"
    target3.vm.hostname = "target3"
    target3.vm.network "private_network", ip: "192.168.60.13"
    target3.vm.provider "virtualbox" do |vb|
      vb.memory = "2048"
      vb.cpus = 1
      vb.name = "config-drift-target3"
    end
  end
end
