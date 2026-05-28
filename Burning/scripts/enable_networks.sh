#!/bin/bash

#enable network on imc and acc

IMC_IP="100.0.0.100"
ACC_IP="ACC"

add_proxy_jump() {
cat << EOF > ~/.ssh/config
Host IMC
HostName 100.0.0.100
user root
StrictHostKeyChecking no
         
Host ACC
HostName 192.168.96.2
user root
ProxyJump IMC
StrictHostKeyChecking no

EOF
}

add_proxy_jump

sed -i /100.0.0.100/d ~/.ssh/known_hosts;
sed -i /192.168.96.2/d ~/.ssh/known_hosts;
sudo sed -i /100.0.0.100/d /root/.ssh/known_hosts;
sudo sed -i /192.168.96.2/d /root/.ssh/known_hosts;

sudo ip a a 100.0.0.1/24 dev eth1
sudo ip link set up dev eth1

ssh -o StrictHostKeyChecking=no root@100.0.0.100 "modprobe icc_net; ifconfig eth2 192.168.96.1 netmask 255.255.255.0 up"

