#!/bin/bash

# Load config from .env if variables aren't set
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi

# Fallbacks if .env is missing/empty
INT_WIFI=${WAN_INTERFACE:-wlp1s0}
INT_LAN=${LAN_INTERFACE:-enp2s0}
IPT="/usr/sbin/iptables"

echo "Configuring Firewall Rules on WAN: $INT_WIFI / LAN: $INT_LAN..."

# 1. FLUSH EVERYTHING (Start Clean)
$IPT -F
$IPT -t nat -F
$IPT -X

# 2. ENABLE NAT (Allow Internet Sharing)
$IPT -t nat -A POSTROUTING -o $INT_WIFI -j MASQUERADE

# 3. ALLOW ESTABLISHED TRAFFIC (Replies from internet)
$IPT -A FORWARD -i $INT_WIFI -o $INT_LAN -m state --state RELATED,ESTABLISHED -j ACCEPT

# 4. ALLOW DNS (Critical for the popup to trigger)
$IPT -A FORWARD -i $INT_LAN -p udp --dport 53 -j ACCEPT
$IPT -A FORWARD -i $INT_LAN -p tcp --dport 53 -j ACCEPT

# 5. THE HIJACK RULE (Captive Portal)
# Redirect any HTTP (Port 80) traffic to Django (Port 8000)
$IPT -t nat -A PREROUTING -i $INT_LAN -p tcp --dport 80 -j DNAT --to-destination 192.168.50.1:8000

# 6. REJECT HTTPS (Fast Fallback Optimization)
# Forces phones to fallback to HTTP immediately instead of waiting for timeout
$IPT -A FORWARD -i $INT_LAN -p tcp --dport 443 -j REJECT --reject-with tcp-reset

# 7. ALLOW ACCESS TO DJANGO
$IPT -A INPUT -i $INT_LAN -p tcp --dport 8000 -j ACCEPT
$IPT -A INPUT -i $INT_LAN -p udp --dport 53 -j ACCEPT

# 8. LOCK THE DOOR (Block everything else)
$IPT -A FORWARD -i $INT_LAN -j DROP

echo "✅ Firewall Configured. Portal Active."
