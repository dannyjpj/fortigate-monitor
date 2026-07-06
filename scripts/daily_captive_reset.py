#!/usr/bin/env python3

import yaml
import secrets
import string
import subprocess
from datetime import datetime

BASE = "/opt/fortigate-monitor"
CONFIG = f"{BASE}/config.yaml"
CSV = f"{BASE}/data/captive_passwords_today.csv"
CLI = f"{BASE}/data/fortigate_reset_passwords.cli"


def gen_password(length):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


config = yaml.safe_load(open(CONFIG))

fg = config["fortigate"]
users = config["captive_portal"]["users"]
length = config["captive_portal"].get("password_length", 10)

host = fg["host"]
ssh_user = fg.get("ssh_user", "admin")
ssh_port = str(fg.get("ssh_port", 22))

today = datetime.now().strftime("%Y-%m-%d")

passwords = []

with open(CSV, "w") as f:
    f.write("fecha,usuario,password\n")

    for user in users:
        password = gen_password(length)
        passwords.append((user, password))
        f.write(f"{today},{user},{password}\n")

with open(CLI, "w") as f:
    f.write("config user local\n")

    for user, password in passwords:
        f.write(f'    edit "{user}"\n')
        f.write(f'        set passwd "{password}"\n')
        f.write("    next\n")

    f.write("end\n")

cmd = [
    "ssh",
    "-i", "/root/.ssh/fortigate_monitor",
    "-p", ssh_port,
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "IdentitiesOnly=yes",
    f"{ssh_user}@{host}",
]

with open(CLI, "r") as f:
    result = subprocess.run(cmd, stdin=f, text=True)

if result.returncode != 0:
    print("ERROR: no se pudo aplicar el reset en FortiGate")
    exit(result.returncode)

print("Reset diario aplicado correctamente")
print(CSV)
