import subprocess
import re
import requests
import base64
from datetime import datetime
from django.conf import settings
from typing import Optional, Dict, Any

def get_mac_address(ip_address: str) -> Optional[str]:
    """
    Retrieves the MAC address corresponding to an IP address from the system ARP table.

    Args:
        ip_address (str): The target IP address (e.g., '192.168.50.133').

    Returns:
        Optional[str]: The MAC address in 'xx:xx:xx:xx:xx:xx' format, or None if not found.
    """
    try:
        with open('/proc/net/arp') as f:
            data = f.read()
        
        for line in data.split('\n'):
            if ip_address in line:
                # ARP file format: IP address ... HW address ...
                parts = line.split()
                for part in parts:
                    # Regex matches standard MAC address format
                    if re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", part):
                        return part
        return None
    except IOError as e:
        # Log error in production
        return None

def trigger_stk_push(phone_number: str, amount: int, reference_id: int) -> Dict[str, Any]:
    """
    Initiates an M-Pesa Express (STK Push) request via the Daraja API.

    Args:
        phone_number (str): The formatted phone number (e.g., '2547...').
        amount (int): The amount to charge in KES.
        reference_id (int): The internal transaction ID to link the payment.

    Returns:
        Dict[str, Any]: The JSON response from Safaricom containing CheckoutRequestID.
    """
    # 1. Generate Auth Token
    try:
        auth_url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        auth_response = requests.get(
            auth_url, 
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
        )
        auth_response.raise_for_status()
        access_token = auth_response.json().get('access_token')
    except Exception as e:
        return {"error": f"Authentication Failed: {str(e)}"}

    # 2. Prepare Payload
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp
    password = base64.b64encode(password_str.encode()).decode('utf-8')
    
    # Construct Callback URL using the environment-specific domain
    callback_url = f"https://{settings.NGROK_DOMAIN}/billing/callback/"

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": f"Wifi_{reference_id}",
        "TransactionDesc": "Internet Access"
    }

    # 3. Send Request
    try:
        api_url = f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(api_url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": f"API Request Failed: {str(e)}"}

def allow_device(user_ip: str, mac_address: Optional[str] = None) -> bool:
    """
    Configures the Linux Kernel Firewall (iptables) to allow internet access for a device.
    
    Strategy:
    1. Insert ACCEPT rule into FORWARD chain (Layer 3).
    2. Insert ACCEPT rule into NAT PREROUTING chain (Layer 2 Bypass) to stop Captive Portal redirection.
    
    Args:
        user_ip (str): The device's local IP address.
        mac_address (str, optional): The device's MAC address for stricter security.

    Returns:
        bool: True if commands executed successfully, False otherwise.
    """
    try:
        # Layer 3: Forwarding
        subprocess.run(["sudo", "iptables", "-I", "FORWARD", "1", "-s", user_ip, "-j", "ACCEPT"], check=True)
        # Layer 2: NAT Bypass (Stop Hijacking)
        subprocess.run(["sudo", "iptables", "-t", "nat", "-I", "PREROUTING", "1", "-s", user_ip, "-j", "ACCEPT"], check=True)
        
        # Layer 2: MAC Filtering (Security Enhancement)
        if mac_address and mac_address != "00:00:00:00:00:00":
            # Best effort: If MAC module fails, we still rely on IP rules
            subprocess.run(
                ["sudo", "iptables", "-I", "FORWARD", "1", "-m", "mac", "--mac-source", mac_address, "-j", "ACCEPT"], 
                check=False
            )
        return True
    except subprocess.CalledProcessError:
        return False

def revoke_device(user_ip: str, mac_address: Optional[str] = None) -> bool:
    """
    Removes a device's access rules from the Linux Firewall.
    """
    try:
        # Remove IP Rules
        subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", user_ip, "-j", "ACCEPT"], check=False)
        subprocess.run(["sudo", "iptables", "-t", "nat", "-D", "PREROUTING", "-s", user_ip, "-j", "ACCEPT"], check=False)
        
        # Remove MAC Rules
        if mac_address:
            subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-m", "mac", "--mac-source", mac_address, "-j", "ACCEPT"], check=False)
        return True
    except Exception:
        return False
