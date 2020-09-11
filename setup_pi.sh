#!/bin/bash
HASEDUROAM=$(awk '/eduroam/' /etc/wpa_supplicant/wpa_supplicant.conf)

if [[ -z $HASEDUROAM ]]; then
    echo -n "Wifi identity (xxx@uva.nl): "
    read WIFI_IDENTITY
    echo -n "Wifi password: "
    read WIFI_PASSWORD

    sudo bash -c "sed 's/IDENTITY/$WIFI_IDENTITY/;s/PASSWORD/$WIFI_PASSWORD/' network_template.conf >>/etc/wpa_supplicant/wpa_supplicant.conf"
fi

sudo systemctl restart networking.service
sudo systemctl restart wpa_supplicant.service
sudo systemctl restart dhcpcd.service

echo "Waiting for a route to become available..."
while :; do
	ROUTELINE=$(route -n | awk '/wlan0/ && $2 != "0.0.0.0"')
	if [[ -n $ROUTELINE ]]; then
		break;
	fi
	sleep 1;
done

if [[ -e "/etc/systemd/system/ssh-forward.service" ]]; then
    echo "Updating ssh-forward.service..."
    NEWPORT=$(perl -n -e '/([A-Za-z0-9]+):localhost:22/ && print $1' /etc/systemd/system/ssh-forward.service)
    TUNNEL_ENDPOINT=$(perl -n -e '/scanner@([a-z.]+)/ && print $1' /etc/systemd/system/ssh-forward.service)
    sudo bash -c "sed 's/POORT/$NEWPORT/;s/ENDPOINT/$TUNNEL_ENDPOINT/' ssh-forward.service >/etc/systemd/system/ssh-forward.service"
    sudo systemctl daemon-reload
    sudo systemctl restart ssh-forward.service
else
    # set up ssh
    mkdir -p ~/.ssh
    echo "Generating SSH keys..."
    ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ""
    chmod 700 ~/.ssh

    echo "Go copy the SSH key to the server (starting a shell...)"
    bash

    echo "Setting up SSH forward service..."
    echo -n "Tunnel endpoint: "
    read TUNNEL_ENDPOINT

    scp scanner@$TUNNEL_ENDPOINT:last_port .
    read PORT <last_port
    let NEWPORT=($PORT + 1)

    ssh scanner@$TUNNEL_ENDPOINT "echo $NEWPORT >last_port"

    sudo bash -c "sed 's/POORT/$NEWPORT/;s/ENDPOINT/$TUNNEL_ENDPOINT/' ssh-forward.service >/etc/systemd/system/ssh-forward.service"
    sudo systemctl daemon-reload
    sudo systemctl enable --now ssh-forward.service
    echo "Forwarding port $NEWPORT on remote to 22 localhost (sshd)."

    echo "Enabling sshd listening on localhost..."
    sudo sed -i -e "s/#ListenAddress 0.0.0.0/ListenAddress localhost/" /etc/ssh/sshd_config
    sudo systemctl enable --now ssh.service
fi

echo "Installing scanner.service..."
sudo cp scanner.service /etc/systemd/system
echo "To enable the scanner service on boot, run 'systemctl enable scanner.service'."

echo -n "Endpoint for scanner data: "
read SCANNER_ENDPOINT

echo -n "Zone for scanner (C or G): "
read SCANNER_ZONE

sed -i -e "s/ENDPOINT/$SCANNER_ENDPOINT/;s/ZONE/$SCANNER_ZONE/" read_events.py
