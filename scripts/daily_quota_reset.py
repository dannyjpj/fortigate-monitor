#!/usr/bin/env python3

import os
import sys
import sqlite3
import yaml

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from modules.fortigate_manager import FortiGateManager
from modules.timezone import local_timestamp
from modules.audit import log_event

DB = f"{BASE}/data/traffic.db"
CONFIG = f"{BASE}/config.yaml"


def ensure_schema(cursor):
    cursor.execute("""
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quota_offsets (
        date TEXT NOT NULL,
        srcip TEXT NOT NULL,
        offset_bytes INTEGER NOT NULL DEFAULT 0,
        reset_at TEXT,
        reset_by TEXT,
        PRIMARY KEY (date, srcip)
    )
    """)


def main():
    config = yaml.safe_load(open(CONFIG))
    quota_cfg = config.get("quota", {})
    group = quota_cfg.get("blocked_group", "BLOQUEADOS_2GB")

    fg = FortiGateManager(config["fortigate"])
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    cur = conn.cursor()
    ensure_schema(cur)

    cur.execute("""
        SELECT srcip, firewall_object
        FROM quota_status
        WHERE status = 'BLOCKED'
          AND firewall_synced = 1
          AND firewall_object IS NOT NULL
    """)
    rows = cur.fetchall()

    released = 0

    for srcip, obj in rows:
        s1, b1 = fg.remove_from_group(group, obj)
        if s1 not in (200, 404):
            print(f"ERROR quitando {obj} del grupo {group}: {s1} {b1}")
            continue

        s2, b2 = fg.delete_address(obj)
        if s2 not in (200, 404):
            print(f"ERROR eliminando address {obj}: {s2} {b2}")
            continue

        released += 1
        print(f"RELEASED {srcip} -> {obj}")

    cur.execute("DELETE FROM traffic")
    cur.execute("DELETE FROM quota_status")
    cur.execute("DELETE FROM quota_offsets")
    conn.commit()
    conn.close()

    now = local_timestamp()
    print(f"Reset diario completado: {released} bloqueos liberados, trafico diario limpiado ({now})")
    log_event(
        DB,
        "daily_quota_reset",
        f"Reset diario de cuotas completado: {released} bloqueos liberados",
        severity="info",
        details={"released": released, "completed_at": now}
    )


if __name__ == "__main__":
    main()
