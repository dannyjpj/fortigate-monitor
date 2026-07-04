#!/usr/bin/env python3

import sqlite3

DB = "/opt/fortigate-monitor/data/traffic.db"
LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("""
SELECT srcip,
       ROUND(SUM(sentbyte + rcvdbyte) / 1024.0 / 1024.0 / 1024.0, 2) AS gb
FROM traffic
GROUP BY srcip
HAVING SUM(sentbyte + rcvdbyte) >= ?
ORDER BY gb DESC
""", (LIMIT_BYTES,))

rows = cursor.fetchall()

for ip, gb in rows:
    print(f"{ip} {gb}GB")

conn.close()
