import sqlite3

from modules.audit import ensure_audit_table

DB_FILE = "/opt/fortigate-monitor/data/traffic.db"


class Database:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, timeout=30)
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS traffic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            hora TEXT,
            network TEXT,
            srcip TEXT,
            srcmac TEXT,
            srcname TEXT,
            dstip TEXT,
            dstmac TEXT,
            policyid INTEGER,
            policyname TEXT,
            service TEXT,
            app TEXT,
            action TEXT,
            sentbyte INTEGER,
            rcvdbyte INTEGER,
            duration INTEGER
        )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_network ON traffic(network)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_srcip ON traffic(srcip)"
        )

        self.ensure_column(cursor, "traffic", "srcmac", "TEXT")
        self.ensure_column(cursor, "traffic", "dstmac", "TEXT")

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_srcmac ON traffic(srcmac)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fecha ON traffic(fecha)"
        )

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

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_quota_status ON quota_status(status)"
        )

        ensure_audit_table(self.conn)

        self.conn.commit()

    def ensure_column(self, cursor, table, column, definition):
        columns = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})")]

        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def insert(self, data):
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO traffic (
            fecha,
            hora,
            network,
            srcip,
            srcmac,
            srcname,
            dstip,
            dstmac,
            policyid,
            policyname,
            service,
            app,
            action,
            sentbyte,
            rcvdbyte,
            duration
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("fecha"),
            data.get("hora"),
            data.get("network"),
            data.get("srcip"),
            data.get("srcmac"),
            data.get("srcname"),
            data.get("dstip"),
            data.get("dstmac"),
            data.get("policyid"),
            data.get("policyname"),
            data.get("service"),
            data.get("app"),
            data.get("action"),
            data.get("sentbyte"),
            data.get("rcvdbyte"),
            data.get("duration")
        ))

        self.conn.commit()

    def purge(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM traffic")
        self.conn.commit()
        print("Base diaria limpiada.")

    def close(self):
        self.conn.close()
