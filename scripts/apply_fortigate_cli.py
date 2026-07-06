#!/usr/bin/env python3

import yaml
import subprocess

CONFIG = "/opt/fortigate-monitor/config.yaml"
CLI_FILE = "/opt/fortigate-monitor/data/fortigate_reset_passwords.cli"

config = yaml.safe_load(open(CONFIG))

host = config["fortigate"]["host"]
user = config["fortigate"].get("ssh_user", "admin")
port = str(config["fortigate"].get("ssh_port", 22))

cmd = [
    "ssh",
    "-i", "/root/.ssh/fortigate_monitor",
    "-p", port,
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "IdentitiesOnly=yes",
    f"{user}@{host}"
]

with open(CLI_FILE, "r") as f:
    result = subprocess.run(
        cmd,
        stdin=f,
        text=True
    )

if result.returncode == 0:
    print("CLI aplicado correctamente en FortiGate")
else:
    print("Error aplicando CLI en FortiGate")
    exit(result.returncode)
