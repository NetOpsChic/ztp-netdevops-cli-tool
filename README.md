# 🚀 Zero Touch Provisioning (ZTP) Server

Dynamic, vendor-aware ZTP server built for modern NetDevOps workflows.  
This ain't your 1900s TFTP/DHCP setup — this is hardened, auto-rendered, API-driven provisioning with style.  
Yes, I **hardcoded MAC addresses** — because let’s be real: dynamic IPs are cute until you want *reliable* automation.

---

## ✨ Features

- ✅ Built-in **Kea DHCP**, **TFTP**, and **REST API**
- 🎯 **MAC-to-IP reservations** from a single YAML source of truth
- 🧠 Auto-generates **vendor-specific startup configs** using Jinja2 templates
- 📂 Stores rendered configs under `startup-configs/`
- 🛠️ Provides **Ansible inventory via API** with `ansible_network_os` set per vendor
- 🧵 Plug-and-play for **GNS3**, **QEMU**, or real hardware test labs

Note: This ztp server is specially created for NetDevops-Cli-tool