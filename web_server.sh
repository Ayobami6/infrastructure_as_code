#!/usr/bin/bash

# Nginx web server deploy script

set_up() {

    # check if params are passed
    
    if [[ "$#" -ne 3  ]]; then
        echo "No domain name or project name passed!. Usage web_server.sh <domain_name> <app_name>"
        exit 1
    fi

    #  install nginx
    sudo apt-get update
    sudo apt install nginx -y
    sudo touch /etc/nginx/sites-available/$2
    # link to site enabled
    sudo ln -s /etc/nginx/sites-available/$2 /etc/nginx/sites-enabled/

    ip_address=$(hostname -I | awk '{print $1}')

    # basic http sever config
    server_config="
    server {
        listen 80;
        server_name $1;
        
        location / {
            include proxy_params;
            proxy_pass http://localhost:8000;
        }
    
    }
    "
    sudo sh -c "echo '$server_config' > /etc/nginx/sites-available/$2"

    sudo systemctl restart nginx

}

set_up