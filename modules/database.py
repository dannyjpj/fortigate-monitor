import sqlite3

DB_FILE = "/opt/fortigate-monitor/data/traffic.db"


class Database:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
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
            srcname TEXT,
            dstip TEXT,
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

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fecha ON traffic(fecha)"
        )

        self.conn.commit()

    def insert(self, data):
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO traffic (
            fecha,
            hora,
            network,
            srcip,
            srcname,
            dstip,
            policyid,
            policyname,
            service,
            app,
            action,
            sentbyte,
            rcvdbyte,
            duration
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("fecha"),
            data.get("hora"),
            data.get("network"),
            data.get("srcip"),
            data.get("srcname"),
            data.get("dstip"),
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