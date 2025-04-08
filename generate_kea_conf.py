#!/usr/bin/env python3
from jinja2 import Environment, FileSystemLoader
import yaml
import os
import sys

ENV_VARS = [
    "SUBNET",
    "RANGE_START",
    "RANGE_END",
    "ZTP_IP",
    "ROUTER_IP",
    "DNS_SERVERS",
    "BROADCAST_IP"
]

def generate_kea_conf(yaml_path, output="/etc/kea/kea-dhcp4.conf"):
    print(f"📥 Loading topology from: {yaml_path}")
    print(f"📤 Will write final Kea config to: {output}")
    
    # 🌍 Print environment values
    env_data = {}
    print("🌍 Environment values:")
    for var in ENV_VARS:
        val = os.getenv(var)
        if not val:
            print(f"❌ ENV ERROR: {var} is not set")
            sys.exit(1)
        env_data[var] = val
        print(f"  {var} = {val}")

    # Load Jinja2 template from the 'templates' directory
    env = Environment(loader=FileSystemLoader("templates"))
    try:
        kea_template = env.get_template("kea-dhcp4.conf.j2")
    except Exception as e:
        print(f"❌ Failed to load kea-dhcp4.conf.j2 template: {e}")
        sys.exit(1)

    # Load topology YAML
    try:
        with open(yaml_path) as f:
            topo = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to read or parse topology file {yaml_path}: {e}")
        sys.exit(1)

    # Generate static reservations
    devices = []
    base_ip = [192, 168, 100, 10]

    for i, node in enumerate(topo.get("network-device", [])):
        reserved_ip = f"{base_ip[0]}.{base_ip[1]}.{base_ip[2]}.{base_ip[3] + i}"
        device = {
            "hostname": node.get("hostname", f"device{i+1}"),
            "mac_address": node.get("mac_address", f"00:00:00:00:00:{i+10:02x}"),
            "reserved_ip": reserved_ip,
            "vendor": node.get("vendor", "arista"),
            "config": node.get("config", [])
        }
        print(f"🖧 Reservation: {device['hostname']} → {device['mac_address']} → {device['reserved_ip']}")
        devices.append(device)

    # ✅ Generate startup-configs (.cfg) per device
    cfg_output_dir = "/var/lib/tftpboot"
    try:
        os.makedirs(cfg_output_dir, exist_ok=True)
        for device in devices:
            vendor_template = f"{device['vendor']}.j2"
            try:
                cfg_template = env.get_template(vendor_template)
                rendered_cfg = cfg_template.render(
                    hostname=device["hostname"],
                    ip=device["reserved_ip"],
                    mac=device["mac_address"],
                    interfaces=device.get("config", [])
                )
                cfg_path = os.path.join(cfg_output_dir, f"{device['hostname']}.cfg")
                with open(cfg_path, "w") as cfg_file:
                    cfg_file.write(rendered_cfg)
                print(f"📄 Generated: {cfg_path}")
            except Exception as e:
                print(f"⚠️ Failed to render {vendor_template} for {device['hostname']}: {e}")
    except Exception as e:
        print(f"❌ Failed generating .cfg files: {e}")
        sys.exit(1)

    # Combine devices and env vars into template context
    context = {
        "devices": devices,
        "host_reservation_identifiers": ["hw-address"],
        **env_data
    }

    # Render kea-dhcp4 config
    try:
        rendered_config = kea_template.render(**context)
    except Exception as e:
        print(f"❌ Jinja2 rendering error for kea config: {e}")
        sys.exit(1)

    # Write final Kea config
    try:
        with open(output, "w") as f:
            f.write(rendered_config)
        print(f"✅ Kea config successfully written to: {output}")
    except Exception as e:
        print(f"❌ Failed to write Kea config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/topology.yaml"
    generate_kea_conf(yaml_path)
