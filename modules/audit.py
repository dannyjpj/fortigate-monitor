import json
import sqlite3

from modules.timezone import local_timestamp


def ensure_audit_table(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'info',
        actor TEXT,
        target TEXT,
        message TEXT NOT NULL,
        details TEXT
    )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)"
    )


def log_event(db_path, event_type, message, severity="info", actor="system", target=None, details=None):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    ensure_audit_table(conn)

    payload = None
    if details is not None:
        payload = json.dumps(details, ensure_ascii=True, default=str)

    conn.execute("""
        INSERT INTO audit_events (
            created_at, event_type, severity, actor, target, message, details
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        local_timestamp(),
        event_type,
        severity,
        actor,
        target,
        message,
        payload
    ))
    conn.commit()
    conn.close()
