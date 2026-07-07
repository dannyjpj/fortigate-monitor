import sqlite3

DB_FILE = "/opt/fortigate-monitor/data/traffic.db"


class Reports:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, timeout=30)
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.row_factory = sqlite3.Row

    def top_ips(self, limit=10):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                srcip,
                COALESCE(MAX(NULLIF(srcname,'')), srcip) AS srcname,
                COALESCE(MAX(NULLIF(network,'')), '-') AS network,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            GROUP BY srcip
            ORDER BY bytes DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def top_services(self, limit=10):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                service,
                COUNT(*) AS conexiones,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            GROUP BY service
            ORDER BY bytes DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def top_apps(self, limit=10):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                app,
                COUNT(*) AS conexiones,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            GROUP BY app
            ORDER BY bytes DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def top_policies(self, limit=10):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                policyname,
                COUNT(*) AS conexiones,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            GROUP BY policyname
            ORDER BY bytes DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def traffic_by_network(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                network,
                COUNT(*) AS conexiones,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            GROUP BY network
            ORDER BY bytes DESC
        """)

        return cursor.fetchall()

    def top_destinations(self, limit=10):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                dstip,
                COUNT(*) AS conexiones,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            GROUP BY dstip
            ORDER BY bytes DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def dashboard(self):

        return {

        "top_ips": [dict(x) for x in self.top_ips()],

        "top_services": [dict(x) for x in self.top_services()],

        "top_apps": [dict(x) for x in self.top_apps()],

        "top_policies": [dict(x) for x in self.top_policies()],

        "top_destinations": [dict(x) for x in self.top_destinations()],

        "traffic_networks": [dict(x) for x in self.traffic_by_network()]

        }
        
    def summary(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT srcip) AS equipos,
                COUNT(*) AS sesiones,
                COUNT(DISTINCT service) AS servicios,
                COUNT(DISTINCT dstip) AS destinos,
                COUNT(DISTINCT policyname) AS politicas,
                COUNT(DISTINCT app) AS aplicaciones,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
        """)

        return dict(cursor.fetchone())


    def close(self):
        self.conn.close()
