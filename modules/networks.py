import ipaddress
import yaml


class NetworkManager:

    def __init__(self, config_file="/opt/fortigate-monitor/config.yaml"):

        with open(config_file, "r") as f:
            cfg = yaml.safe_load(f)

        self.networks = []

        for network in cfg.get("networks", []):

            self.networks.append({
                "name": network["name"],
                "subnet": ipaddress.ip_network(network["subnet"])
            })

    def get_network(self, ip):

        try:
            ip = ipaddress.ip_address(ip)
        except ValueError:
            return "UNKNOWN"

        for network in self.networks:

            if ip in network["subnet"]:
                return network["name"]

        return "UNKNOWN"

class NetworkClassifier:

    def __init__(self, networks_config):
        self.networks = []

        for item in networks_config:
            name = item["name"]
            subnet = ipaddress.ip_network(item["subnet"])
            self.networks.append((name, subnet))

    def get_network(self, ip):
        try:
            ip_obj = ipaddress.ip_address(ip)
        except Exception:
            return None

        for name, subnet in self.networks:
            if ip_obj in subnet:
                return name

        return None