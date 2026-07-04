#!/usr/bin/env python3

import os
import sys
import sqlite3
import yaml
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from modules.fortigate_manager import FortiGateManager

DB = f"{BASE}/data/traffic.db"
CONFIG = f"{BASE}/config.yaml"

LIMIT_GB = 2
LIMIT_BYTES = LIMIT_GB * 1024 * 1024 * 1024
GROUP = "BLOQUEADOS_2GB"

today = datetime.now().strftime("%Y-%m-%d")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

config = yaml.safe_load(open(CONFIG))
fg = FortiGateManager(config["fortigate"])

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT srcip,
       SUM(sentbyte + rcvdbyte) AS used_bytes
FROM traffic
WHERE fecha = ?
GROUP BY srcip
HAVING used_bytes >= ?
""", (today, LIMIT_BYTES))

rows = cur.fetchall()

for srcip, used_bytes in rows:
    used_gb = round(used_bytes / 1024 / 1024 / 1024, 2)
    obj = f"BLOCK_{srcip}"

    cur.execute("""
    SELECT status, firewall_synced
    FROM quota_status
    WHERE date = ? AND srcip = ?
    """, (today, srcip))

    existing = cur.fetchone()

    if existing:
        status_db, synced = existing

        if status_db == "RELEASED":
            continue

        if synced == 1:
            continue

    name, s1, b1 = fg.create_address(srcip)

    if s1 not in (200, 201, 500):
        print(f"ERROR creando address {srcip}: {s1} {b1}")
        continue

    s2, b2 = fg.add_to_group(GROUP, obj)

    if s2 not in (200, 201):
        print(f"ERROR agregando al grupo {srcip}: {s2} {b2}")
        continue

    cur.execute("""
    INSERT OR REPLACE INTO quota_status
    (date, srcip, used_bytes, used_gb, limit_gb, status, blocked_at, firewall_object, firewall_synced)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        today,
        srcip,
        used_bytes,
        used_gb,
        LIMIT_GB,
        "BLOCKED",
        now,
        obj,
        1
    ))

    print(f"BLOCKED {srcip} {used_gb}GB -> {obj}")

conn.commit()
conn.close()
