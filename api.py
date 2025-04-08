from flask import Flask, jsonify, request
import os
import csv
import yaml
import requests
import logging
import json
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)

# Define file paths (adjust if necessary)
LEASES_FILE = "/var/lib/kea/kea-leases4.csv"
INVENTORY_FILE = "/ansible_inventory/hosts"
TOPOLOGY_FILE = "/tmp/topology.yaml"
TOPOLOGY_URL="http://localhost:5000/topology"

def parse_inventory():
    """Parses the Ansible inventory file and returns a dictionary grouped by vendor."""
    if not os.path.exists(INVENTORY_FILE):
        return {}
    inventory = {}
    current_group = None
    with open(INVENTORY_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Lines like [cisco] indicate a vendor group
            if line.startswith("[") and line.endswith("]"):
                current_group = line[1:-1]
                inventory[current_group] = []
            else:
                if current_group:
                    inventory[current_group].append(line)
    return inventory

def parse_inventory():
    """Parses the JSON Ansible inventory file and returns it as a dict."""
    if not os.path.exists("/ansible_inventory/inventory.json"):
        return {}
    with open("/ansible_inventory/inventory.json", "r") as f:
        return json.load(f)

def load_topology():
    topology_url = os.environ.get("TOPOLOGY_URL")

    # Use uploaded local YAML first if present
    if os.path.exists(TOPOLOGY_FILE):
        try:
            with open(TOPOLOGY_FILE, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    # Try remote fetch silently (no log output)
    if topology_url:
        try:
            response = requests.get(topology_url, timeout=2)
            response.raise_for_status()
            return yaml.safe_load(response.text)
        except Exception:
            return {}

    return {}


@app.route("/inventory", methods=["POST"])
def upload_inventory():
    """
    API endpoint to accept inventory JSON uploads (e.g., from ZTP generator).
    Saves uploaded inventory to INVENTORY_FILE.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400
    try:
        os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
        with open(INVENTORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print("✅ Inventory uploaded via POST and saved to", INVENTORY_FILE)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/inventory", methods=["GET"])
def get_inventory():
    """API endpoint to get the current Ansible inventory as JSON."""
    inventory = parse_inventory()
    return jsonify(inventory)

@app.route("/leases", methods=["GET"])
def get_leases():
    """API endpoint to get the current DHCP leases as JSON."""
    leases = parse_leases()
    return jsonify(leases)

@app.route("/topology", methods=["GET"])
def get_topology():
    """
    API endpoint to return the topology.
    
    The topology is fetched dynamically:
      - First, from a remote URL if the TOPOLOGY_URL environment variable is set.
      - Otherwise, from the local file.
    """
    topology = load_topology()
    return jsonify(topology)

@app.route("/upload-yaml", methods=["POST"])
def upload_yaml():
    """
    API endpoint to upload a YAML file.
    
    The YAML file is expected to be passed as form-data under the key "file".
    It is validated and then stored as TOPOLOGY_FILE (local fallback) for use in your ZTP flow.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    try:
        content = file.read()
        # Validate the YAML content by attempting to parse it
        topology = yaml.safe_load(content)
        # Save the file locally (as defined by TOPOLOGY_FILE)
        with open(TOPOLOGY_FILE, "w") as f:
            f.write(content.decode("utf-8"))
        return jsonify({"message": "YAML file uploaded and saved successfully"}), 200
    except yaml.YAMLError as e:
        return jsonify({"error": f"YAML parsing error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    # Listen on all interfaces on port 5000
    app.run(host="0.0.0.0", port=5000)
