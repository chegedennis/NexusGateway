# 📡 NexusGateway: Commercial ISP Management System

**A full-stack, automated Captive Portal solution integrating Linux Kernel networking with Mobile Money payments.**

NexusGateway transforms standard Linux hardware into a commercial-grade Wi-Fi vending machine. It serves as a middleware layer between raw hardware interfaces (iptables/dnsmasq) and fintech APIs (Safaricom M-Pesa), automating the entire lifecycle of internet access management.



## 🚀 Key Engineering Features

### 1. Cyber-Physical System
Unlike standard web apps, NexusGateway directly manipulates the host operating system.
* **Kernel-Level Control:** Uses Python to execute raw Bash commands for `iptables` (Firewall) and `sysctl` (Kernel Forwarding).
* **Layer 2 & 3 Filtering:** Manages access control lists (ACLs) using both IP addresses and hardware MAC addresses to prevent spoofing.

### 2. Fintech Integration (M-Pesa)
* **Real-Time Payments:** Integrated Safaricom Daraja API for STK Push (Lipa na M-Pesa Online).
* **Asynchronous Processing:** Implemented Python `threading` to handle API handshakes in the background, preventing UI blocking during payment initiation.
* **Idempotent Callbacks:** Robust webhook handling to process payment confirmations securely.

### 3. Automated Resilience
* **Session Watchdog:** A background daemon (`session_monitor.py`) that monitors active sessions and automatically revokes firewall access upon expiration.
* **Self-Healing Network:** Includes a master boot script (`service_daemon.sh`) that auto-configures network topology, DHCP leases, and IP forwarding on reboot.
* **Offline-First UI:** Solved the "Captive Portal Latency" problem by embedding all CSS/Assets directly into the DOM, ensuring instant load times on disconnected devices.

---

## 🛠️ Architecture

* **Gateway:** Debian Linux (Router/NAT/DHCP)
* **Backend:** Django 5 (Python 3.10+)
* **Database:** SQLite (Dev) / PostgreSQL (Prod)
* **Tunneling:** Ngrok (Secure Webhook Exposure)
* **Networking:**
    * `dnsmasq` (DHCP Server)
    * `iptables` (NAT Masquerading & Packet Filtering)

## 📦 Installation

### Prerequisites
* Linux Environment (Debian/Ubuntu/Kali)
* Two Network Interfaces (e.g., `wlp1s0` for WAN, `enp2s0` for LAN)
* Root/Sudo privileges

### Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/chegedennis/NexusGateway.git](https://github.com/chegedennis/NexusGateway.git)
    cd NexusGateway
    ```

2.  **Environment Configuration**
    Create a `.env` file in the root directory:
    ```ini
    # Django
    SECRET_KEY=your-secure-key
    DEBUG=True
    ALLOWED_HOSTS=*

    # Network Config
    WAN_INTERFACE=wlp1s0
    LAN_INTERFACE=enp2s0
    NGROK_DOMAIN=your-static-domain.ngrok-free.dev

    # M-Pesa Keys (Sandbox)
    MPESA_CONSUMER_KEY=your_key
    MPESA_CONSUMER_SECRET=your_secret
    MPESA_PASSKEY=your_passkey
    MPESA_SHORTCODE=174379
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    sudo apt install dnsmasq iptables
    ```

4.  **Initialize System**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

## ⚡ Usage

Run the master daemon to start the network stack, tunnels, and application server:

```bash
./service_daemon.sh
