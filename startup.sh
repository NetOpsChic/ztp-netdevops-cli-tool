#!/bin/bash

# ✅ Environment Variables
export ZTP_IP=${ZTP_IP:-192.168.100.3}
export SUBNET=${SUBNET:-192.168.100.0}
export NETMASK=${NETMASK:-255.255.255.0}
export RANGE_START=${RANGE_START:-192.168.100.100}
export RANGE_END=${RANGE_END:-192.168.100.200}
export ROUTER_IP=${ROUTER_IP:-192.168.100.4}
export DNS_SERVERS=${DNS_SERVERS:-"8.8.8.8, 8.8.4.4"}
export BROADCAST_IP=${BROADCAST_IP:-192.168.100.255}

VENDOR="arista"
TOPOLOGY_URL="http://localhost:5000/topology"
KEA_CONF="/etc/kea/kea-dhcp4.conf"
TFTP_DIR=${TFTP_DIR:-/var/lib/tftpboot}
LEASE_FILE="/var/lib/kea/kea-leases4.csv"

# ✅ Assign static IP to eth0
echo "🚀 Assigning static IP to eth0 - ZTP IP: $ZTP_IP/24"
ip addr add "$ZTP_IP/24" dev eth0 || echo "⚠️ Failed to assign static IP"
ip link set eth0 up

# ✅ Start API early
echo "🚀 Starting API server..."
export TOPOLOGY_URL
python3 /usr/local/bin/api.py &
sleep 3

# ✅ Wait for API to be ready
echo "⏳ Waiting for API server at $TOPOLOGY_URL ..."
for i in {1..30}; do
  if curl -s "$TOPOLOGY_URL" > /dev/null; then
    echo "✅ API server is reachable!"
    break
  fi
  echo "🔄 Waiting for API... ($i/30)"
  sleep 3
done

# ✅ Fetch topology and generate Kea config dynamically
TOPOLOGY_FILE=$(mktemp /tmp/topology.XXXX.yaml)
curl -s "$TOPOLOGY_URL" -o "$TOPOLOGY_FILE"
if [ -s "$TOPOLOGY_FILE" ]; then
  echo "✅ Topology fetched. Generating Kea config..."
  python3 /usr/local/bin/generate_kea_conf.py "$TOPOLOGY_FILE"
else
  echo "❌ Failed to fetch topology. Using fallback kea.conf."
fi

# ✅ Runtime prep
echo "🚀 Preparing runtime directories..."
mkdir -p /var/run/kea /run/kea /var/log/kea /var/lib/kea "$TFTP_DIR"
chmod 755 /var/run/kea /run/kea /var/log/kea /var/lib/kea
chmod 777 "$TFTP_DIR"
touch "$LEASE_FILE"
chmod 644 "$LEASE_FILE"

# ✅ Start Kea
echo "🚀 Starting Kea DHCP Server..."
kea-dhcp4 -c "$KEA_CONF" > /var/log/kea/kea-dhcp4.log 2>&1 &
sleep 2

# ✅ Start TFTP
echo "🚀 Starting TFTP Server at $TFTP_DIR ..."
service tftpd-hpa stop
/usr/sbin/in.tftpd -l -s "$TFTP_DIR" --verbose --foreground &

# ✅ Start Nginx
echo "🚀 Starting Nginx..."
service nginx restart || { echo "❌ Failed to start Nginx"; exit 1; }

# ✅ Wait for DHCP leases
echo "⏳ Waiting for active DHCP leases..."
for i in {1..30}; do
  if grep -qE "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" "$LEASE_FILE"; then
    echo "✅ Lease detected."
    break
  fi
  echo "🔄 Still waiting for DHCP leases... ($i/30)"
  sleep 10
done

# ✅ Small delay to allow routers to request DHCP
echo "⏳ Waiting 40s to ensure routers complete ZTP..."
sleep 60

# ✅ Sleep then generate configs
echo "🚀 Generating inventory and configs into $TFTP_DIR..."
python3 /usr/local/bin/generate_inventory.py --vendor "$VENDOR" --output-dir "$TFTP_DIR"

echo "✅ ZTP Server is fully operational and serving from $TFTP_DIR!"
tail -f /dev/null
