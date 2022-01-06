#/bin/bash

set -e

# install gps-script dependancies
echo "Installing dependancies"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pip python3-zmq
pip3 install pyserial

# enable gps-collector service
echo "Starting gps-collector service"
echo -e "[Install]\nWantedBy=multi-user.target\n" > /lib/systemd/system/gps-collector.service
echo -e "[Unit]\nDescription=Collectiong location information" >> /lib/systemd/system/gps-collector.service
echo -e "After=network.target docker.service\n" >> /lib/systemd/system/gps-collector.service
echo -e "[Service]\nExecStart=/usr/bin/python3 /home/monroeSA/gps-collector/gps-dump.py\n" >> /lib/systemd/system/gps-collector.service
echo -e "Type=simple\nRestart=on-failure\n" >> /lib/systemd/system/gps-collector.service
echo -e "StandardError=null\nStandardOutput=null\n" >> /lib/systemd/system/gps-collector.service

systemctl enable gps-collector.service
systemctl start gps-collector.service
