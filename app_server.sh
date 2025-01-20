#!/usr/bin/bash

# Django app server deployment script

set_up() {

# Validate input
if [ -z "$1" ]; then
    echo "Error: No Django app name provided. Usage: ./app_server.sh <django_app_name>"
    exit 1
fi

# Install required packages
sudo apt update
sudo apt install python3-venv python3-pip redis-server -y || { echo "Package installation failed"; exit 1; }

# Create and activate virtual environment
python3 -m venv venv || { echo "Failed to create virtual environment"; exit 1; }
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt || { echo "Failed to install Python dependencies"; exit 1; }
pip install gunicorn

# Enable and start Redis
sudo systemctl enable redis
sudo systemctl start redis || { echo "Failed to start Redis"; exit 1; }

# Create Gunicorn service file
cwd=$(pwd)
user=$(whoami)
service_config="
[Unit]
Description=Gunicorn instance to serve Django App
After=network.target

[Service]
User=$user
Group=www-data
WorkingDirectory=$cwd
Environment=\"PATH=$cwd/venv/bin\"
ExecStart=$cwd/venv/bin/gunicorn --access-logfile - --workers 3 --bind 0.0.0.0:8000 $1.wsgi:application

[Install]
WantedBy=multi-user.target
"

sudo sh -c "echo '$service_config' > /etc/systemd/system/$1.service"
sudo systemctl daemon-reload
sudo systemctl start $1.service || { echo "Failed to start Gunicorn service"; exit 1; }
sudo systemctl enable $1.service || { echo "Failed to enable Gunicorn service"; exit 1; }
}

set_up "$@"
