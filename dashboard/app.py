import sqlite3
from datetime import datetime
from flask import jsonify
from flask import Flask, render_template
import sys
import os

# Permite importar los módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.reports import Reports
from modules.config import Config
from modules.fortigate_manager import FortiGateManager

app = Flask(__name__)

from dashboard.utils import format_bytes

app.jinja_env.filters["bytes"] = format_bytes

@app.route("/")
def index():

    cfg = Config().get()
    firewall = cfg["fortigate"]["name"]

    r = Reports()

    summary = r.summary()
    dashboard = r.dashboard()

    r.close()

    return render_template(
        "index.html",
        firewall=firewall,
        summary=summary,
        equipos=len(dashboard["top_ips"]),
        servicios=len(dashboard["top_services"]),
        destinos=len(dashboard["top_destinations"]),
        redes=len(dashboard["traffic_networks"]),
        dashboard=dashboard
    )


@app.route("/api/dashboard")
def api_dashboard():

    cfg = Config().get()
    firewall = cfg["fortigate"]["name"]

    r = Reports()

    data = {
        "firewall": firewall,
        "summary": r.summary(),
        "equipos": len(r.top_ips(1000)),
        "servicios": len(r.top_services(1000)),
        "destinos": len(r.top_destinations(1000)),
        "redes": len(r.traffic_by_network()),
        "dashboard": r.dashboard()
    }

    r.close()

    return jsonify(data)

@app.route("/quotas")
def quotas():
    cfg = Config().get()
    db = cfg["general"]["database"]

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT date, srcip, used_gb, limit_gb, status,
               blocked_at, firewall_object, firewall_synced
        FROM quota_status
        ORDER BY used_gb DESC
    """)

    quotas = cur.fetchall()
    conn.close()

    return render_template("quotas.html", quotas=quotas)

@app.route("/api/quota/release/<ip>", methods=["POST"])
def release_quota(ip):
    cfg = Config().get()
    db = cfg["general"]["database"]
    fg = FortiGateManager(cfg["fortigate"])

    obj = f"BLOCK_{ip}"

    s1, b1 = fg.remove_from_group("BLOQUEADOS_2GB", obj)
    s2, b2 = fg.delete_address(obj)

    if s1 not in (200, 404) or s2 not in (200, 404):
        return jsonify({
            "status": "error",
            "remove_group": [s1, b1],
            "delete_address": [s2, b2]
        }), 500

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""
        UPDATE quota_status
        SET status='RELEASED',
            firewall_object=NULL,
            firewall_synced=0
        WHERE srcip=?
    """, (ip,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "ip": ip})

if __name__ == "__main__":
		
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
