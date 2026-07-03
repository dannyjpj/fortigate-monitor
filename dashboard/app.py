from flask import jsonify
from flask import Flask, render_template
import sys
import os

# Permite importar los módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.reports import Reports
from modules.config import Config

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


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
