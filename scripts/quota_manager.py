#!/usr/bin/env python3

import os
import sys
import sqlite3
import yaml
import fcntl

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from modules.fortigate_manager import FortiGateManager
from modules.timezone import local_date, local_timestamp
from modules.audit import log_event

DB = f"{BASE}/data/traffic.db"
CONFIG = f"{BASE}/config.yaml"
LOCK_FILE = "/tmp/fortigate_quota_manager.lock"

lock_fd = open(LOCK_FILE, "w")

try:
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("quota_manager ya esta en ejecucion; se omite este ciclo")
    sys.exit(0)

config = yaml.safe_load(open(CONFIG))
quota_cfg = config.get("quota", {})

LIMIT_GB = float(quota_cfg.get("limit_gb", 2))
LIMIT_BYTES = LIMIT_GB * 1024 * 1024 * 1024
GROUP = quota_cfg.get("blocked_group", "BLOQUEADOS_2GB")

today = local_date()
now = local_timestamp()

fg = FortiGateManager(config["fortigate"])

conn = sqlite3.connect(DB, timeout=30)
conn.execute("PRAGMA busy_timeout = 30000")
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA synchronous = NORMAL")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS quota_status (
    date TEXT NOT NULL,
    srcip TEXT NOT NULL,
    used_bytes INTEGER NOT NULL DEFAULT 0,
    used_gb REAL NOT NULL DEFAULT 0,
    limit_gb REAL NOT NULL DEFAULT 2,
    status TEXT NOT NULL DEFAULT 'BLOCKED',
    blocked_at TEXT,
    firewall_object TEXT,
    firewall_synced INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, srcip)
)
""")

cur.execute(
    "CREATE INDEX IF NOT EXISTS idx_quota_status ON quota_status(status)"
)

cur.execute("""
CREATE TABLE IF NOT EXISTS quota_offsets (
    date TEXT NOT NULL,
    srcip TEXT NOT NULL,
    offset_bytes INTEGER NOT NULL DEFAULT 0,
    reset_at TEXT,
    reset_by TEXT,
    PRIMARY KEY (date, srcip)
)
""")

cur.execute("""
WITH usage AS (
    SELECT srcip,
           SUM(sentbyte + rcvdbyte) AS total_bytes
    FROM traffic
    WHERE fecha = ?
    GROUP BY srcip
)
SELECT usage.srcip,
       CASE
           WHEN usage.total_bytes - COALESCE(quota_offsets.offset_bytes, 0) < 0 THEN 0
           ELSE usage.total_bytes - COALESCE(quota_offsets.offset_bytes, 0)
       END AS used_bytes
FROM usage
LEFT JOIN quota_offsets
    ON quota_offsets.date = ?
   AND quota_offsets.srcip = usage.srcip
WHERE CASE
        WHEN usage.total_bytes - COALESCE(quota_offsets.offset_bytes, 0) < 0 THEN 0
        ELSE usage.total_bytes - COALESCE(quota_offsets.offset_bytes, 0)
      END >= ?
""", (today, today, LIMIT_BYTES))

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
            cur.execute("""
            UPDATE quota_status
            SET used_bytes = ?,
                used_gb = ?,
                limit_gb = ?,
                status = 'BLOCKED'
            WHERE date = ? AND srcip = ?
            """, (used_bytes, used_gb, LIMIT_GB, today, srcip))
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

    conn.commit()

    print(f"BLOCKED {srcip} {used_gb}GB -> {obj}")

    try:
        log_event(
            DB,
            "quota_blocked",
            f"IP {srcip} bloqueada por superar {LIMIT_GB}GB",
            severity="warning",
            target=srcip,
            details={
                "used_gb": used_gb,
                "limit_gb": LIMIT_GB,
                "firewall_object": obj,
                "group": GROUP
            }
        )
    except sqlite3.OperationalError as exc:
        print(f"WARN auditoria cuota {srcip}: {exc}")

conn.commit()
conn.close()
