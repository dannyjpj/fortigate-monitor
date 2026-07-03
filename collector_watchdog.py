#!/usr/bin/env python3

import yaml
import ipaddress
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ===============================
# Cargar configuración
# ===============================

with open("/opt/fortigate-monitor/config.yaml", "r") as f:
    config = yaml.safe_load(f)

LOG_FILE = config["general"]["log_file"]

NETWORKS = [
    ipaddress.ip_network(net["subnet"])
    for net in config["networks"]
]

# ===============================
# Funciones
# ===============================

def extract_srcip(line):
    """
    Extrae srcip= de una línea del FortiGate.
    """
    for field in line.split():
        if field.startswith("srcip="):
            return field.split("=")[1]
    return None


def ip_allowed(ip):
    """
    Verifica si la IP pertenece a alguna red monitoreada.
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
    except Exception:
        return False

    return any(ip_obj in net for net in NETWORKS)


# ===============================
# Watchdog
# ===============================

class LogHandler(FileSystemEventHandler):

    def on_modified(self, event):

        if event.src_path != LOG_FILE:
            return

        with open(LOG_FILE, "r") as f:

            f.seek(0, 2)

            while True:

                line = f.readline()

                if not line:
                    break

                ip = extract_srcip(line)

                if ip and ip_allowed(ip):
                    print(line.strip())


observer = Observer()
observer.schedule(LogHandler(), path="/var/log", recursive=False)
observer.start()

print("Collector iniciado...")

try:

    while True:
        time.sleep(1)

except KeyboardInterrupt:

    observer.stop()

observer.join()
