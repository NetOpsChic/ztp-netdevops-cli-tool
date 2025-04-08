#!/usr/bin/env python3
import os
import csv
import json
import yaml
import requests

KEA_LEASES_FILE = "/var/lib/kea/kea-leases4.csv"
TOPOLOGY_FILE = "/tmp/topology.yaml"
OUTPUT_PATH = "/ansible_inventory/inventory.json"
UPLOAD_URL = "http://localhost:5000/inventory"

def parse_topology_mac_to_hostname(yaml_path):
    if not os.path.exists(yaml_path):
        print(f"[WARN] Topology file not found: {yaml_path}")
        return {}
    with open(yaml_path, "r") as f:
        try:
            topo = yaml.safe_load(f)
        except Exception as e:
            print(f"[ERROR] Failed to parse topology YAML: {e}")
            return {}
    mac_to_hostname = {}
    for node in topo.get("network-device", []):
        mac = node.get("mac_address", "").lower()
        if mac:
            mac_to_hostname[mac] = node.get("hostname", "")
    return mac_to_hostname

def parse_kea_leases(mac_to_hostname):
    leases = {}
    with open(KEA_LEASES_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ip = row["address"].strip()
                mac = row["hwaddr"].strip().lower().replace("-", ":")
                timestamp = int(row["expire"])
                if not mac or not ip:
                    continue
                hostname = mac_to_hostname.get(mac)
                if not hostname:
                    continue
                if mac not in leases or timestamp > leases[mac]["timestamp"]:
                    leases[mac] = {
                        "ip": ip,
                        "timestamp": timestamp,
                        "hostname": hostname
                    }
            except Exception as e:
                print(f"[WARN] Skipping row due to error: {e}")
                continue
    return leases

def write_inventory(leases):
    inventory = {
        "all": {
            "hosts": [],
            "vars": {}
        }
    }
    for lease in leases.values():
        hostname = lease["hostname"]
        ip = lease["ip"]
        inventory["all"]["hosts"].append(hostname)
        inventory[hostname] = {
            "ansible_host": ip,
            "ansible_user": "admin",
            "ansible_password": "admin",
            "ansible_connection": "network_cli",
            "ansible_network_os": "eos"
        }
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(inventory, f, indent=2)
    print(f"✅ Inventory written to {OUTPUT_PATH}")
    return inventory

def upload_inventory(inventory):
    print(f"📡 Uploading inventory to: {UPLOAD_URL}")
    try:
        response = requests.post(UPLOAD_URL, json=inventory)
        if response.status_code == 200:
            print("✅ Inventory uploaded successfully.")
        else:
            print(f"❌ Upload failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Exception during inventory upload: {e}")

def generate_inventory():
    mac_to_hostname = parse_topology_mac_to_hostname(TOPOLOGY_FILE)
    leases = parse_kea_leases(mac_to_hostname)
    if leases:
        inventory = write_inventory(leases)
        upload_inventory(inventory)
    else:
        print("❌ No valid leases found.")

if __name__ == "__main__":
    generate_inventory()
