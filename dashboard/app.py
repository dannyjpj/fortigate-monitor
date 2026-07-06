import csv
import sqlite3
import sys
import os
import secrets
import string
import subprocess
from datetime import datetime
from functools import wraps

from flask import send_file
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from werkzeug.security import check_password_hash

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.reports import Reports
from modules.config import Config
from modules.fortigate_manager import FortiGateManager
from dashboard.utils import format_bytes

app = Flask(__name__)

cfg = Config().get()
app.secret_key = cfg["dashboard"]["secret_key"]
app.jinja_env.filters["bytes"] = format_bytes


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    cfg = Config().get()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        for user in cfg["users"]:
            if user["username"] == username and check_password_hash(user["password_hash"], password):
                session["logged_in"] = True
                session["username"] = username
                session["role"] = user.get("role", "admin")
                return redirect(url_for("index"))

        error = "Usuario o contraseña incorrectos"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
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
@login_required
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
@login_required
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
        WHERE status='BLOCKED'
        ORDER BY used_gb DESC
    """)

    quotas = cur.fetchall()
    conn.close()

    return render_template("quotas.html", quotas=quotas)


@app.route("/api/quota/release/<ip>", methods=["POST"])
@login_required
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

@app.route("/portal")
@login_required
def portal():
    cfg = Config().get()
    csv_file = "/opt/fortigate-monitor/data/captive_passwords_today.csv"

    users = []

    if os.path.exists(csv_file):
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row)

    return render_template("portal.html", users=users)

@app.route("/download/captive-passwords")
@login_required
def download_captive_passwords():
    path = "/opt/fortigate-monitor/data/captive_passwords_today.csv"
    return send_file(path, as_attachment=True)

def gen_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@app.route("/api/portal/reset/<username>", methods=["POST"])
@login_required
def reset_portal_user(username):
    cfg = Config().get()
    fg = cfg["fortigate"]
    length = cfg["captive_portal"].get("password_length", 10)

    password = gen_password(length)

    cli = f'''
config user local
    edit "{username}"
        set passwd "{password}"
    next
end
'''

    cmd = [
    "ssh",
    "-i", "/root/.ssh/fortigate_monitor",
    "-p", str(fg.get("ssh_port", 22)),
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "IdentitiesOnly=yes",
    f'{fg.get("ssh_user", "admin")}@{fg["host"]}',
    ]

    result = subprocess.run(cmd, input=cli, text=True)

    if result.returncode != 0:
        return jsonify({"status": "error"}), 500

    csv_file = "/opt/fortigate-monitor/data/captive_passwords_today.csv"
    today = datetime.now().strftime("%Y-%m-%d")

    rows = []
    if os.path.exists(csv_file):
        with open(csv_file, newline="") as f:
            rows = list(csv.DictReader(f))

    updated = False
    for row in rows:
        if row["usuario"] == username:
            row["fecha"] = today
            row["password"] = password
            updated = True

    if not updated:
        rows.append({"fecha": today, "usuario": username, "password": password})

    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "usuario", "password"])
        writer.writeheader()
        writer.writerows(rows)

    return jsonify({"status": "ok", "username": username})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
