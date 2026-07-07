import csv
import ipaddress
import sqlite3
import sys
import os
import secrets
import shutil
import string
import subprocess
from io import StringIO
from datetime import datetime
from functools import wraps

from flask import send_file
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Response
from werkzeug.security import check_password_hash

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.reports import Reports
from modules.config import Config, CONFIG_FILE
from modules.fortigate_manager import FortiGateManager
from modules.timezone import local_date, local_stamp, local_timestamp
from modules.audit import log_event, ensure_audit_table
from dashboard.utils import format_bytes

app = Flask(__name__)

cfg = Config().get()
app.secret_key = cfg["dashboard"]["secret_key"]
app.jinja_env.filters["bytes"] = format_bytes


def parse_networks(raw):
    networks = []
    errors = []

    for index, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()

        if not line:
            continue

        if "," not in line:
            errors.append(f"Linea {index}: use el formato Nombre, CIDR")
            continue

        name, subnet = [part.strip() for part in line.split(",", 1)]

        if not name:
            errors.append(f"Linea {index}: el nombre de red es obligatorio")
            continue

        try:
            ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            errors.append(f"Linea {index}: CIDR invalido ({subnet})")
            continue

        networks.append({
            "name": name,
            "subnet": subnet
        })

    if not networks:
        errors.append("Debe configurar al menos una red monitoreada")

    return networks, errors


def config_to_networks_text(cfg):
    return "\n".join(
        f'{item.get("name", "")}, {item.get("subnet", "")}'
        for item in cfg.get("networks", [])
    )


def backup_config():
    backup_dir = os.path.join(os.path.dirname(CONFIG_FILE), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = local_stamp()
    backup_path = os.path.join(backup_dir, f"config-{stamp}.yaml")
    shutil.copy2(CONFIG_FILE, backup_path)
    return backup_path


def save_config(cfg):
    import yaml

    backup_path = backup_config()
    tmp_path = f"{CONFIG_FILE}.tmp"

    with open(tmp_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=False)

    os.replace(tmp_path, CONFIG_FILE)
    return backup_path


def restart_collector():
    result = subprocess.run(
        ["systemctl", "restart", "fortigate-monitor"],
        capture_output=True,
        text=True,
        timeout=20
    )
    return result.returncode == 0, result.stderr or result.stdout


def service_state(name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
            timeout=5
        )
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "state": "error",
            "detail": str(exc)
        }

    state = result.stdout.strip() or result.stderr.strip() or "unknown"
    return {
        "name": name,
        "ok": state == "active",
        "state": state,
        "detail": ""
    }


def timer_state(name):
    try:
        active = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()
        enabled = subprocess.run(
            ["systemctl", "is-enabled", name],
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "state": "error",
            "detail": str(exc)
        }

    return {
        "name": name,
        "ok": active == "active",
        "state": active or "unknown",
        "detail": f"enabled: {enabled or 'unknown'}"
    }


def database_health(db_path):
    info = {
        "ok": False,
        "path": db_path,
        "size_mb": 0,
        "traffic_rows": 0,
        "quota_rows": 0,
        "blocked_rows": 0,
        "detail": ""
    }

    try:
        if os.path.exists(db_path):
            info["size_mb"] = round(os.path.getsize(db_path) / 1024 / 1024, 2)

        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA busy_timeout = 10000")
        ensure_audit_table(conn)
        cur = conn.cursor()
        info["traffic_rows"] = cur.execute("SELECT COUNT(*) FROM traffic").fetchone()[0]
        info["quota_rows"] = cur.execute("SELECT COUNT(*) FROM quota_status").fetchone()[0]
        info["blocked_rows"] = cur.execute(
            "SELECT COUNT(*) FROM quota_status WHERE status='BLOCKED'"
        ).fetchone()[0]
        conn.close()
        info["ok"] = True
    except Exception as exc:
        info["detail"] = str(exc)

    return info


def fortigate_health(cfg):
    group = cfg.get("quota", {}).get("blocked_group", "BLOQUEADOS_2GB")
    info = {
        "ok": False,
        "host": cfg.get("fortigate", {}).get("host", "-"),
        "name": cfg.get("fortigate", {}).get("name", "-"),
        "group": group,
        "detail": ""
    }

    try:
        status, data = FortiGateManager(cfg["fortigate"]).get_group(group)
    except Exception as exc:
        info["detail"] = str(exc)
        return info

    info["ok"] = status == 200
    info["detail"] = "Address Group disponible" if status == 200 else f"HTTP {status}: {data}"
    return info


def quota_health(cfg, db_path):
    quota = cfg.get("quota", {})
    info = {
        "limit_gb": quota.get("limit_gb", 2),
        "blocked_group": quota.get("blocked_group", "BLOQUEADOS_2GB"),
        "over_limit": [],
        "detail": ""
    }

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        limit_bytes = float(info["limit_gb"]) * 1024 * 1024 * 1024
        cur.execute("""
            SELECT srcip,
                   ROUND(SUM(sentbyte + rcvdbyte) / 1024.0 / 1024.0 / 1024.0, 2) AS used_gb
            FROM traffic
            WHERE fecha = ?
            GROUP BY srcip
            HAVING SUM(sentbyte + rcvdbyte) >= ?
            ORDER BY used_gb DESC
            LIMIT 5
        """, (local_date(), limit_bytes))
        info["over_limit"] = [dict(row) for row in cur.fetchall()]
        conn.close()
    except Exception as exc:
        info["detail"] = str(exc)

    return info


def monitored_network_for_ip(cfg, ip):
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return "-"

    for item in cfg.get("networks", []):
        try:
            network = ipaddress.ip_network(item.get("subnet", ""), strict=False)
        except ValueError:
            continue
        if address in network:
            return item.get("name") or item.get("subnet")

    return "-"


def clients_inventory(cfg):
    db_path = cfg["general"]["database"]
    quota_cfg = cfg.get("quota", {})
    limit_gb = float(quota_cfg.get("limit_gb", 2))
    limit_bytes = limit_gb * 1024 * 1024 * 1024
    today = local_date()

    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        WITH usage AS (
            SELECT
                srcip,
                COALESCE(MAX(NULLIF(srcname,'')), srcip) AS srcname,
                COALESCE(MAX(NULLIF(network,'')), '-') AS network,
                SUM(sentbyte + rcvdbyte) AS bytes,
                COUNT(*) AS sessions,
                MAX(hora) AS last_seen
            FROM traffic
            WHERE fecha = ?
            GROUP BY srcip
        )
        SELECT
            usage.*,
            quota_status.status AS quota_status,
            quota_status.firewall_synced,
            quota_status.blocked_at,
            quota_status.firewall_object
        FROM usage
        LEFT JOIN quota_status
            ON quota_status.date = ?
           AND quota_status.srcip = usage.srcip
        ORDER BY usage.bytes DESC
    """, (today, today))

    rows = []
    summary = {
        "total": 0,
        "normal": 0,
        "warning": 0,
        "blocked": 0,
        "released": 0
    }

    for row in cur.fetchall():
        item = dict(row)
        used_bytes = item.get("bytes") or 0
        used_gb = round(used_bytes / 1024 / 1024 / 1024, 2)
        percent = round((used_bytes / limit_bytes) * 100, 1) if limit_bytes else 0
        capped = min(percent, 100)

        raw_status = item.get("quota_status")

        if raw_status == "BLOCKED":
            status = "blocked"
            status_label = "Bloqueado"
        elif raw_status == "RELEASED":
            status = "released"
            status_label = "Liberado"
        elif percent >= 80:
            status = "warning"
            status_label = "Cerca del limite"
        else:
            status = "normal"
            status_label = "Normal"

        summary["total"] += 1
        summary[status] += 1

        item.update({
            "used_gb": used_gb,
            "used_label": format_bytes(used_bytes),
            "percent": percent,
            "capped": capped,
            "status": status,
            "status_label": status_label,
            "limit_gb": limit_gb
        })
        rows.append(item)

    conn.close()
    return rows, summary


def client_detail_data(cfg, ip):
    db_path = cfg["general"]["database"]
    quota_cfg = cfg.get("quota", {})
    limit_gb = float(quota_cfg.get("limit_gb", 2))
    limit_bytes = limit_gb * 1024 * 1024 * 1024
    today = local_date()

    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COALESCE(MAX(NULLIF(srcname,'')), ?) AS srcname,
            COALESCE(MAX(NULLIF(network,'')), ?) AS network,
            SUM(sentbyte + rcvdbyte) AS bytes,
            SUM(sentbyte) AS sentbyte,
            SUM(rcvdbyte) AS rcvdbyte,
            COUNT(*) AS sessions,
            MIN(hora) AS first_seen,
            MAX(hora) AS last_seen
        FROM traffic
        WHERE fecha = ? AND srcip = ?
    """, (ip, monitored_network_for_ip(cfg, ip), today, ip))
    summary = dict(cur.fetchone())
    summary["srcip"] = ip
    summary["bytes"] = summary.get("bytes") or 0
    summary["sentbyte"] = summary.get("sentbyte") or 0
    summary["rcvdbyte"] = summary.get("rcvdbyte") or 0
    summary["sessions"] = summary.get("sessions") or 0
    summary["used_label"] = format_bytes(summary["bytes"])
    summary["sent_label"] = format_bytes(summary["sentbyte"])
    summary["received_label"] = format_bytes(summary["rcvdbyte"])
    summary["percent"] = round((summary["bytes"] / limit_bytes) * 100, 1) if limit_bytes else 0
    summary["capped"] = min(summary["percent"], 100)

    cur.execute("""
        SELECT status, blocked_at, firewall_object, firewall_synced, used_gb, limit_gb
        FROM quota_status
        WHERE date = ? AND srcip = ?
        LIMIT 1
    """, (today, ip))
    quota_row = cur.fetchone()
    quota = dict(quota_row) if quota_row else {
        "status": "NORMAL",
        "blocked_at": None,
        "firewall_object": None,
        "firewall_synced": 0,
        "used_gb": round(summary["bytes"] / 1024 / 1024 / 1024, 2),
        "limit_gb": limit_gb
    }

    def top_query(field, label, limit=10):
        cur.execute(f"""
            SELECT
                COALESCE(NULLIF({field}, ''), '-') AS label,
                COUNT(*) AS sessions,
                SUM(sentbyte + rcvdbyte) AS bytes
            FROM traffic
            WHERE fecha = ? AND srcip = ?
            GROUP BY COALESCE(NULLIF({field}, ''), '-')
            ORDER BY bytes DESC
            LIMIT ?
        """, (today, ip, limit))
        return [
            {
                "label": row["label"],
                "sessions": row["sessions"],
                "bytes": row["bytes"],
                "bytes_label": format_bytes(row["bytes"] or 0)
            }
            for row in cur.fetchall()
        ]

    detail = {
        "summary": summary,
        "quota": quota,
        "services": top_query("service", "service"),
        "destinations": top_query("dstip", "dstip"),
        "policies": top_query("policyname", "policyname"),
        "apps": top_query("app", "app")
    }

    conn.close()
    return detail


def quota_center_data(cfg):
    db_path = cfg["general"]["database"]
    limit_gb = float(cfg.get("quota", {}).get("limit_gb", 2))
    limit_bytes = limit_gb * 1024 * 1024 * 1024
    today = local_date()

    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT date, srcip, used_gb, limit_gb, status,
           blocked_at, firewall_object, firewall_synced
        FROM quota_status
        WHERE date = ?
        ORDER BY
            CASE status WHEN 'BLOCKED' THEN 0 WHEN 'RELEASED' THEN 1 ELSE 2 END,
            used_gb DESC
    """, (today,))
    rows = [dict(row) for row in cur.fetchall()]

    cur.execute("""
        SELECT srcip,
               COALESCE(MAX(NULLIF(srcname,'')), srcip) AS srcname,
               COALESCE(MAX(NULLIF(network,'')), '-') AS network,
               SUM(sentbyte + rcvdbyte) AS bytes,
               COUNT(*) AS sessions
        FROM traffic
        WHERE fecha = ?
        GROUP BY srcip
        HAVING SUM(sentbyte + rcvdbyte) >= ?
        ORDER BY bytes DESC
    """, (today, limit_bytes))
    over_limit = []
    for row in cur.fetchall():
        item = dict(row)
        item["used_gb"] = round((item["bytes"] or 0) / 1024 / 1024 / 1024, 2)
        item["used_label"] = format_bytes(item["bytes"] or 0)
        over_limit.append(item)

    conn.close()

    return {
        "rows": rows,
        "over_limit": over_limit,
        "summary": {
            "blocked": sum(1 for row in rows if row["status"] == "BLOCKED"),
            "released": sum(1 for row in rows if row["status"] == "RELEASED"),
            "over_limit": len(over_limit),
            "limit_gb": limit_gb,
            "group": cfg.get("quota", {}).get("blocked_group", "-")
        }
    }


def audit_events(db_path, limit=100):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    ensure_audit_table(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT created_at, event_type, severity, actor, target, message, details
        FROM audit_events
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def portal_inventory(cfg):
    csv_file = cfg.get("captive_portal", {}).get(
        "csv_file",
        "/opt/fortigate-monitor/data/captive_passwords_today.csv"
    )

    users = []
    last_rotation = "-"

    if os.path.exists(csv_file):
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row)
                if row.get("fecha") and (last_rotation == "-" or row["fecha"] > last_rotation):
                    last_rotation = row["fecha"]

    return users, {
        "users": len(users),
        "last_rotation": last_rotation,
        "csv_file": csv_file,
        "csv_exists": os.path.exists(csv_file),
        "password_length": cfg.get("captive_portal", {}).get("password_length", 10)
    }


def diagnostics_data(cfg):
    db_path = cfg["general"]["database"]
    checks = []

    def add(name, ok, detail, category="Sistema"):
        checks.append({
            "name": name,
            "ok": bool(ok),
            "detail": detail,
            "category": category
        })

    add("Config YAML", os.path.exists(CONFIG_FILE), CONFIG_FILE, "Archivos")
    add("Base de datos", os.path.exists(db_path), db_path, "Archivos")
    add("Directorio data", os.path.isdir(os.path.dirname(db_path)), os.path.dirname(db_path), "Archivos")
    add("FortiGate host", bool(cfg.get("fortigate", {}).get("host")), cfg.get("fortigate", {}).get("host", "-"), "FortiGate")
    add("FortiGate API token", bool(cfg.get("fortigate", {}).get("api_token")), "Token configurado" if cfg.get("fortigate", {}).get("api_token") else "Token no configurado", "FortiGate")

    fg = fortigate_health(cfg)
    add("Address Group de bloqueo", fg["ok"], fg["detail"], "FortiGate")

    for service in ("fortigate-dashboard", "fortigate-monitor", "fortigate-collector"):
        state = service_state(service)
        add(service, state["ok"], state["state"], "Servicios")

    purge = timer_state("fortigate-purge.timer")
    add("fortigate-purge.timer", purge["ok"], f"{purge['state']} / {purge['detail']}", "Servicios")

    db = database_health(db_path)
    add("SQLite saludable", db["ok"], db["detail"] or f"{db['traffic_rows']} filas de trafico", "Base de datos")

    return checks


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


@app.route("/health")
@login_required
def health():
    cfg = Config().get()
    db_path = cfg["general"]["database"]
    services = [
        service_state("fortigate-dashboard"),
        service_state("fortigate-monitor"),
        service_state("fortigate-collector"),
    ]
    purge_timer = timer_state("fortigate-purge.timer")
    db = database_health(db_path)
    fg = fortigate_health(cfg)
    quota = quota_health(cfg, db_path)

    overall_ok = (
        all(item["ok"] for item in services[:2])
        and purge_timer["ok"]
        and db["ok"]
        and fg["ok"]
    )

    return render_template(
        "health.html",
        checked_at=local_timestamp(),
        overall_ok=overall_ok,
        services=services,
        purge_timer=purge_timer,
        db=db,
        fg=fg,
        quota=quota,
        networks=cfg.get("networks", []),
        timezone=cfg.get("general", {}).get("timezone", "America/Lima")
    )


@app.route("/clients")
@login_required
def clients():
    cfg = Config().get()
    rows, summary = clients_inventory(cfg)

    return render_template(
        "clients.html",
        clients=rows,
        summary=summary,
        quota=cfg.get("quota", {}),
        checked_at=local_timestamp()
    )


@app.route("/clients/<ip>")
@login_required
def client_detail(ip):
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return redirect(url_for("clients"))

    cfg = Config().get()
    detail = client_detail_data(cfg, ip)

    return render_template(
        "client_detail.html",
        ip=ip,
        detail=detail,
        quota_config=cfg.get("quota", {}),
        checked_at=local_timestamp()
    )


@app.route("/events")
@login_required
def events():
    cfg = Config().get()
    rows = audit_events(cfg["general"]["database"], 150)

    summary = {
        "total": len(rows),
        "warnings": sum(1 for row in rows if row["severity"] == "warning"),
        "errors": sum(1 for row in rows if row["severity"] == "error"),
        "info": sum(1 for row in rows if row["severity"] == "info")
    }

    return render_template(
        "events.html",
        events=rows,
        summary=summary,
        checked_at=local_timestamp()
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
    data = quota_center_data(cfg)

    return render_template(
        "quotas.html",
        quotas=data["rows"],
        over_limit=data["over_limit"],
        summary=data["summary"],
        checked_at=local_timestamp()
    )


@app.route("/download/traffic-report.csv")
@login_required
def download_traffic_report():
    cfg = Config().get()
    rows, _ = clients_inventory(cfg)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "fecha",
        "srcip",
        "srcname",
        "network",
        "used_gb",
        "used_label",
        "quota_percent",
        "status",
        "sessions",
        "last_seen"
    ])

    for row in rows:
        writer.writerow([
            local_date(),
            row.get("srcip"),
            row.get("srcname"),
            row.get("network"),
            row.get("used_gb"),
            row.get("used_label"),
            row.get("percent"),
            row.get("status_label"),
            row.get("sessions"),
            row.get("last_seen")
        ])

    filename = f"traffic-report-{local_date()}.csv"
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/quota/release/<ip>", methods=["POST"])
@login_required
def release_quota(ip):
    cfg = Config().get()
    db = cfg["general"]["database"]
    group = cfg.get("quota", {}).get("blocked_group", "BLOQUEADOS_2GB")

    fg = FortiGateManager(cfg["fortigate"])
    obj = f"BLOCK_{ip}"

    s1, b1 = fg.remove_from_group(group, obj)
    s2, b2 = fg.delete_address(obj)

    if s1 not in (200, 404) or s2 not in (200, 404):
        return jsonify({
            "status": "error",
            "remove_group": [s1, b1],
            "delete_address": [s2, b2]
        }), 500

    conn = sqlite3.connect(db, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
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
    log_event(
        db,
        "quota_released",
        f"IP {ip} liberada manualmente",
        severity="info",
        actor=session.get("username", "admin"),
        target=ip,
        details={
            "firewall_object": obj,
            "group": group,
            "remove_group_status": s1,
            "delete_address_status": s2
        }
    )

    return jsonify({"status": "ok", "ip": ip})


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    cfg = Config().get()
    quota_cfg = cfg.setdefault("quota", {})
    fortigate_cfg = cfg.setdefault("fortigate", {})
    portal_cfg = cfg.setdefault("captive_portal", {})
    general_cfg = cfg.setdefault("general", {})
    message = None
    error = None
    backup_path = None

    form = {
        "firewall_name": fortigate_cfg.get("name", ""),
        "firewall_host": fortigate_cfg.get("host", ""),
        "ssh_user": fortigate_cfg.get("ssh_user", "admin"),
        "ssh_port": str(fortigate_cfg.get("ssh_port", 22)),
        "timezone": general_cfg.get("timezone", "America/Lima"),
        "password_length": str(portal_cfg.get("password_length", 10)),
        "limit_gb": str(quota_cfg.get("limit_gb", 2)),
        "blocked_group": quota_cfg.get("blocked_group", "BLOQUEADOS_2GB"),
        "networks": config_to_networks_text(cfg)
    }

    if request.method == "POST":
        form["firewall_name"] = request.form.get("firewall_name", "").strip()
        form["firewall_host"] = request.form.get("firewall_host", "").strip()
        form["ssh_user"] = request.form.get("ssh_user", "").strip()
        form["ssh_port"] = request.form.get("ssh_port", "").strip()
        form["timezone"] = request.form.get("timezone", "").strip()
        form["password_length"] = request.form.get("password_length", "").strip()
        form["limit_gb"] = request.form.get("limit_gb", "").strip()
        form["blocked_group"] = request.form.get("blocked_group", "").strip()
        form["networks"] = request.form.get("networks", "").strip()

        errors = []
        ssh_port = fortigate_cfg.get("ssh_port", 22)
        password_length = portal_cfg.get("password_length", 10)

        if not form["firewall_name"]:
            errors.append("El nombre del FortiGate es obligatorio")

        if not form["firewall_host"]:
            errors.append("El host/IP del FortiGate es obligatorio")

        if not form["ssh_user"]:
            errors.append("El usuario SSH es obligatorio")

        try:
            ssh_port = int(form["ssh_port"])
            if ssh_port <= 0 or ssh_port > 65535:
                errors.append("El puerto SSH debe estar entre 1 y 65535")
        except ValueError:
            errors.append("El puerto SSH debe ser numerico")

        if not form["timezone"]:
            errors.append("La zona horaria es obligatoria")

        try:
            password_length = int(form["password_length"])
            if password_length < 8 or password_length > 32:
                errors.append("La longitud de password debe estar entre 8 y 32")
        except ValueError:
            errors.append("La longitud de password debe ser numerica")

        try:
            limit_gb = float(form["limit_gb"])
            if limit_gb <= 0:
                errors.append("El limite de cuota debe ser mayor que 0")
        except ValueError:
            errors.append("El limite de cuota debe ser numerico")

        if not form["blocked_group"]:
            errors.append("El grupo de bloqueo es obligatorio")
        else:
            try:
                proposed_fortigate = dict(cfg["fortigate"])
                proposed_fortigate.update({
                    "name": form["firewall_name"],
                    "host": form["firewall_host"],
                    "ssh_user": form["ssh_user"],
                    "ssh_port": ssh_port
                })
                status, _ = FortiGateManager(proposed_fortigate).get_group(form["blocked_group"])
            except Exception as exc:
                errors.append(f"No se pudo validar el grupo en FortiGate: {exc}")
            else:
                if status != 200:
                    errors.append(
                        f"El grupo {form['blocked_group']} no existe como Address Group en FortiGate"
                    )

        networks, network_errors = parse_networks(form["networks"])
        errors.extend(network_errors)

        if errors:
            error = " | ".join(errors)
        else:
            cfg["fortigate"].update({
                "name": form["firewall_name"],
                "host": form["firewall_host"],
                "ssh_user": form["ssh_user"],
                "ssh_port": ssh_port
            })
            cfg["general"]["timezone"] = form["timezone"]
            cfg["captive_portal"]["password_length"] = password_length
            cfg["quota"] = {
                "limit_gb": limit_gb,
                "blocked_group": form["blocked_group"]
            }
            cfg["networks"] = networks

            try:
                backup_path = save_config(cfg)
                restarted, restart_output = restart_collector()
            except Exception as exc:
                error = f"No se pudo guardar la configuracion: {exc}"
            else:
                if restarted:
                    message = "Configuracion guardada y collector reiniciado correctamente"
                else:
                    message = "Configuracion guardada, pero no se pudo reiniciar el collector"
                    error = restart_output or "Revise systemctl status fortigate-monitor"
                log_event(
                    cfg["general"]["database"],
                    "configuration_updated",
                    "Configuracion operativa actualizada desde UI",
                    severity="info" if restarted else "warning",
                    actor=session.get("username", "admin"),
                    details={
                        "limit_gb": limit_gb,
                        "blocked_group": form["blocked_group"],
                        "networks": networks,
                        "firewall_name": form["firewall_name"],
                        "firewall_host": form["firewall_host"],
                        "ssh_user": form["ssh_user"],
                        "ssh_port": ssh_port,
                        "timezone": form["timezone"],
                        "password_length": password_length,
                        "backup": backup_path,
                        "collector_restarted": restarted
                    }
                )

                cfg = Config().get()
                form["networks"] = config_to_networks_text(cfg)
                form["firewall_name"] = cfg.get("fortigate", {}).get("name", form["firewall_name"])
                form["firewall_host"] = cfg.get("fortigate", {}).get("host", form["firewall_host"])
                form["ssh_user"] = cfg.get("fortigate", {}).get("ssh_user", form["ssh_user"])
                form["ssh_port"] = str(cfg.get("fortigate", {}).get("ssh_port", form["ssh_port"]))
                form["timezone"] = cfg.get("general", {}).get("timezone", form["timezone"])
                form["password_length"] = str(cfg.get("captive_portal", {}).get("password_length", form["password_length"]))
                form["limit_gb"] = str(cfg.get("quota", {}).get("limit_gb", limit_gb))
                form["blocked_group"] = cfg.get("quota", {}).get("blocked_group", form["blocked_group"])

    return render_template(
        "settings.html",
        form=form,
        message=message,
        error=error,
        backup_path=backup_path
    )

@app.route("/portal")
@login_required
def portal():
    cfg = Config().get()
    users, summary = portal_inventory(cfg)

    return render_template(
        "portal.html",
        users=users,
        summary=summary,
        checked_at=local_timestamp()
    )


@app.route("/diagnostics")
@login_required
def diagnostics():
    cfg = Config().get()
    checks = diagnostics_data(cfg)
    ok_count = sum(1 for check in checks if check["ok"])
    categories = sorted({check["category"] for check in checks})

    return render_template(
        "diagnostics.html",
        checks=checks,
        categories=categories,
        summary={
            "ok": ok_count,
            "fail": len(checks) - ok_count,
            "total": len(checks)
        },
        checked_at=local_timestamp()
    )

@app.route("/download/captive-passwords")
@login_required
def download_captive_passwords():
    cfg = Config().get()
    path = cfg.get("captive_portal", {}).get(
        "csv_file",
        "/opt/fortigate-monitor/data/captive_passwords_today.csv"
    )
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

    csv_file = cfg.get("captive_portal", {}).get(
        "csv_file",
        "/opt/fortigate-monitor/data/captive_passwords_today.csv"
    )
    today = local_date()

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

    log_event(
        cfg["general"]["database"],
        "portal_password_reset",
        f"Password actualizado para {username}",
        severity="info",
        actor=session.get("username", "admin"),
        target=username
    )

    return jsonify({"status": "ok", "username": username})


@app.route("/api/portal/rotate-all", methods=["POST"])
@login_required
def rotate_all_portal_users():
    cfg = Config().get()
    script = "/opt/fortigate-monitor/scripts/daily_captive_reset.py"

    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
        timeout=180
    )

    ok = result.returncode == 0
    log_event(
        cfg["general"]["database"],
        "portal_password_rotation",
        "Rotacion manual de usuarios del portal cautivo",
        severity="info" if ok else "error",
        actor=session.get("username", "admin"),
        details={
            "returncode": result.returncode,
            "stdout": result.stdout[-1000:],
            "stderr": result.stderr[-1000:]
        }
    )

    if not ok:
        return jsonify({
            "status": "error",
            "message": result.stderr or result.stdout or "No se pudo rotar passwords"
        }), 500

    return jsonify({"status": "ok", "message": "Passwords rotados correctamente"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
