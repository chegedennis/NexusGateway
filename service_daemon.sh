#!/bin/bash

# --- 1. LOAD CONFIGURATION ---
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ ERROR: .env file missing!"
    exit 1
fi

# Log Files
LOG_DJANGO="django.log"
LOG_MONITOR="session_monitor.log"  
LOG_NGROK="ngrok.log"

# --- 2. CLEANUP FUNCTION ---
cleanup() {
    echo ""
    echo "=========================================="
    echo "🛑 STOPPING NEXUS GATEWAY..."
    echo "=========================================="
    
    if [ -n "$NGROK_PID" ]; then 
        echo "   - Killing Ngrok..."
        kill $NGROK_PID 2>/dev/null
    fi
    
    if [ -n "$DJANGO_PID" ]; then 
        echo "   - Killing Django..."
        kill $DJANGO_PID 2>/dev/null
    fi
    
    if [ -n "$MONITOR_PID" ]; then  
        echo "   - Killing Session Monitor..."
        kill $MONITOR_PID 2>/dev/null
    fi
    
    echo "✅ System halted."
    exit
}
trap cleanup SIGINT SIGTERM

echo "=========================================="
echo "   🌅 STARTING NEXUS GATEWAY ($NGROK_DOMAIN) "
echo "=========================================="

# --- 3. NETWORK SETUP ---
echo "[1/4] 🌐 Configuring Network..."

# Enable IP Forwarding
sudo sysctl -w net.ipv4.ip_forward=1 > /dev/null

# Reset LAN IP
echo "      - Setting Static IP on $LAN_INTERFACE..."
sudo ip addr flush dev $LAN_INTERFACE
sudo ip addr add 192.168.50.1/24 dev $LAN_INTERFACE
sudo ip link set $LAN_INTERFACE up

# Apply Firewall
sudo ./net_config.sh

# Restart DHCP
sudo systemctl restart dnsmasq
echo "      ✅ Network Ready."

# --- 4. NGROK STARTUP ---
echo "[2/4] 🚀 Starting Ngrok Tunnel..."
pkill ngrok
ngrok http 8000 --domain=$NGROK_DOMAIN --host-header="localhost:8000" > $LOG_NGROK 2>&1 &
NGROK_PID=$!

echo "      ⏳ Verifying connection..."
TIMEOUT=60
COUNTER=0
while ! curl -s http://127.0.0.1:4040/api/tunnels > /dev/null; do
    sleep 1
    COUNTER=$((COUNTER+1))
    if [ $COUNTER -eq $TIMEOUT ]; then
        echo "❌ ERROR: Ngrok failed to start."
        echo "   Check $LOG_NGROK for details."
        cleanup
    fi
done
echo "      ✅ Ngrok is ONLINE."

# --- 5. DJANGO STARTUP ---
echo "[3/4] 🐍 Starting Portal & Billing..."
python3 -u manage.py runserver 0.0.0.0:8000 > $LOG_DJANGO 2>&1 &
DJANGO_PID=$!
echo "      ✅ Django running (PID: $DJANGO_PID)"

# --- 6. SESSION MONITOR STARTUP ---
echo "[4/4] 👀 Starting Session Monitor..."
# Note: Ensure the management command file is named 'session_monitor.py'
python3 -u manage.py session_monitor > $LOG_MONITOR 2>&1 &
MONITOR_PID=$!
echo "      ✅ Monitor active (PID: $MONITOR_PID)"

echo ""
echo "🎉 SYSTEM IS LIVE! (Press Ctrl+C to stop)"
echo "-----------------------------------------"

# Keep running until user exits
wait
