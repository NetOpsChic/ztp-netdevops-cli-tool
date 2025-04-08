#!/usr/bin/env python3
import netifaces
import ipaddress

def get_interface_ip_and_subnet(interface):
    """
    Get the IP address and netmask of the given interface.
    """
    try:
        addresses = netifaces.ifaddresses(interface)
    except ValueError:
        return None, None
    if netifaces.AF_INET in addresses:
        ip_info = addresses[netifaces.AF_INET][0]
        ip = ip_info.get('addr')
        netmask = ip_info.get('netmask')
        return ip, netmask
    return None, None

def calculate_network_params(ip, netmask):
    """
    Calculate the network, available hosts, CIDR prefix and broadcast address.
    """
    network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
    available_ips = list(network.hosts())
    cidr = network.prefixlen
    broadcast_ip = network.broadcast_address
    return network, available_ips, cidr, broadcast_ip

def main():
    # Use the virbr0 interface explicitly
    interface = "br0"
    if interface not in netifaces.interfaces():
        print(f"# Error: Interface {interface} not found.")
        return

    ip, netmask = get_interface_ip_and_subnet(interface)
    if not ip or not netmask:
        print(f"# Error: Could not retrieve IP/netmask for {interface}.")
        return

    network, available_ips, cidr, broadcast_ip = calculate_network_params(ip, netmask)
    subnet = str(network.network_address)
    netmask_str = netmask  # as reported, e.g. 255.255.255.0

    # Find the position of the interface IP in the available hosts list
    ip_obj = ipaddress.IPv4Address(ip)
    try:
        ip_index = available_ips.index(ip_obj)
    except ValueError:
        print(f"# Error: Interface IP {ip} not in host list.")
        return

    # Ensure there are enough IPs available after the interface IP.
    if ip_index + 3 >= len(available_ips):
        print("# Error: Not enough available IPs after the interface IP.")
        return

    # Select values:
    # - ZTP_IP: first IP after the interface IP.
    # - ROUTER_IP: second IP after the interface IP.
    # - DHCP Pool: from third IP after the interface IP up to the last available host.
    ztp_ip = str(available_ips[ip_index + 1])
    router_ip = str(available_ips[ip_index + 2])
    dhcp_range_start = str(available_ips[ip_index + 3])
    dhcp_range_end = str(available_ips[-1])

    # Output the environment variables in export format.
    print(f"export ZTP_IP={ztp_ip}")
    print(f"export SUBNET={subnet}")
    print(f"export NETMASK={netmask_str}")
    print(f"export CIDR={cidr}")
    print(f"export RANGE_START={dhcp_range_start}")
    print(f"export RANGE_END={dhcp_range_end}")
    print(f"export ROUTER_IP={router_ip}")
    print(f"export BROADCAST_IP={broadcast_ip}")

if __name__ == "__main__":
    main()
