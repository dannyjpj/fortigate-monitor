import time
import yaml
from modules.parser import FortigateParser
from modules.networks import NetworkClassifier
from modules.database import Database

LOG_FILE = "/var/log/fortigate.log"

config = yaml.safe_load(open("/opt/fortigate-monitor/config.yaml"))

parser = FortigateParser()
networks = NetworkClassifier(config["networks"])
db = Database()

print("Collector iniciado...")

with open(LOG_FILE, "r") as f:
    f.seek(0, 2)

    while True:
        line = f.readline()

        if not line:
            time.sleep(1)
            continue

        data = parser.parse(line)

        if not data:
            continue

        if not data.get("srcip"):
            continue

        network = networks.get_network(data["srcip"])

        if not network:
            continue

        data["network"] = network

        db.insert(data)

        print(
            data["fecha"],
            data["hora"],
            data["network"],
            data["srcip"],
            data["sentbyte"] + data["rcvdbyte"]
        )