#!/usr/bin/bash

# set's up Liberty Gaia Monitor

# install setup tools
apt install wget python3 -y

cwd=$(pwd)

# download the gaia script
wget https://raw.githubusercontent.com/Ayobami6/infrastructure_as_code/refs/heads/master/gaia.py

# change permission
chmod +x gaia.py

# create a systemd service for gaia
cat <<EOF > /etc/systemd/system/gaia.service
[Unit]
Description=Gaia Monitor
After=network.target

[Service]
WorkingDirectory=$cwd
ExecStart=python3 gaia.py
Restart=always

StandardOutput=append:/var/log/gaia.log
StandardError=append:/var/log/gaia_error.log
[Install]
WantedBy=multi-user.target
EOF

# reload systemd
systemctl daemon-reload

echo "Please create a config file with the name <celery_service_name.json> "

echo "-> Restart the gaia systemd service once the config file <celery_service_name.json> is created"

echo "Enjoy!, Thank you for installing Gaia"

