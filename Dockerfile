FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV DHCP_INTERFACE=eth0
ENV LEASES_FILE=/var/lib/kea/dhcp4.leases
ENV INVENTORY_DIR=/ansible_inventory
ENV TFTP_DIR=/var/lib/tftpboot

# Install dependencies and ISC repository setup
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/isc/kea-2-6/setup.deb.sh' | bash

# Install required packages including the latest Kea DHCP server
RUN apt-get update && apt-get install -y \
    isc-kea \
    ufw \
    tftpd-hpa \
    nginx \
    python3 \
    python3-pip \
    ansible \
    net-tools \
    iproute2 \
    libcap2-bin \
    jq \
    tcpdump \
    systemd \
    python3-flask \
    curl \
    python3-netifaces \
    python3-psutil \
    && rm -rf /var/lib/apt/lists/*

# Ensure necessary directories exist
RUN mkdir -p /var/lib/kea && touch /var/lib/kea/dhcp4.leases && chmod 644 /var/lib/kea/dhcp4.leases
RUN mkdir -p ${TFTP_DIR} && chmod 777 ${TFTP_DIR}
RUN mkdir -p /etc/kea  # Ensure /etc/kea exists
RUN pip install --break-system-packages paramiko jinja2

# Copy necessary configuration files and scripts
COPY generate_inventory.py /usr/local/bin/generate_inventory.py
COPY startup.sh /usr/local/bin/startup.sh
COPY dynamic_dhcp.py /usr/local/bin/dynamic_dhcp.py
COPY generate_kea_conf.py /usr/local/bin/
COPY templates /templates

# Set execute permissions
RUN chmod +x /usr/local/bin/generate_inventory.py /usr/local/bin/startup.sh /usr/local/bin/generate_kea_conf.py

# Ensure TFTP runs in foreground mode
RUN echo 'TFTP_DIRECTORY="/var/lib/tftpboot"' > /etc/default/tftpd-hpa && \
    echo 'TFTP_OPTIONS="--secure --create --foreground"' >> /etc/default/tftpd-hpa

# Expose required ports
EXPOSE 67/udp 69/udp 80/tcp 5000/tcp

# Create a volume for Ansible inventory
VOLUME ["/ansible_inventory"]

# ---------------------
# API additions start
# ---------------------

# Copy API server file (api.py) into the container
COPY api.py /usr/local/bin/api.py

RUN ufw allow 5000/tcp || true

# ---------------------
# API additions end
# ---------------------

# ✅ Run startup script and keep container running
CMD ["/bin/bash", "/usr/local/bin/startup.sh"]
