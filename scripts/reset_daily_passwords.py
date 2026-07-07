#!/usr/bin/env python3

import yaml
import secrets
import string
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from modules.timezone import local_date

CONFIG = "/opt/fortigate-monitor/config.yaml"
OUTPUT = "/opt/fortigate-monitor/data/captive_passwords_today.csv"


def generate_password(length):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


config = yaml.safe_load(open(CONFIG))

users = config["captive_portal"]["users"]
length = config["captive_portal"].get("password_length", 10)

today = local_date()

with open(OUTPUT, "w") as f:
    f.write("fecha,usuario,password\n")

    for user in users:
        password = generate_password(length)
        f.write(f"{today},{user},{password}\n")
        print(f"{user} {password}")
