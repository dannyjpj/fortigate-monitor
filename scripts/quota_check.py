#!/usr/bin/env python3

import os
import sqlite3

import yaml
from modules.timezone import local_date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = f"{BASE}/data/traffic.db"
CONFIG = f"{BASE}/config.yaml"

config = yaml.safe_load(open(CONFIG))
quota_cfg = config.get("quota", {})

limit_gb = float(quota_cfg.get("limit_gb", 2))
limit_bytes = limit_gb * 1024 * 1024 * 1024
today = local_date()

conn = sqlite3.connect(DB, timeout=30)
conn.execute("PRAGMA busy_timeout = 30000")
cursor = conn.cursor()

cursor.execute("""
SELECT srcip,
       ROUND(SUM(sentbyte + rcvdbyte) / 1024.0 / 1024.0 / 1024.0, 2) AS gb
FROM traffic
WHERE fecha = ?
GROUP BY srcip
HAVING SUM(sentbyte + rcvdbyte) >= ?
ORDER BY gb DESC
""", (today, limit_bytes))

rows = cursor.fetchall()

for ip, gb in rows:
    print(f"{ip} {gb}GB")

conn.close()
