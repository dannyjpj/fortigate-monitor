import requests
import urllib3

urllib3.disable_warnings()

class FortiGateManager:
    def __init__(self, config):
        self.host = config["host"]
        self.token = config["api_token"]
        self.verify_ssl = config.get("verify_ssl", False)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def create_address(self, ip):
        name = f"BLOCK_{ip}"
        url = f"https://{self.host}/api/v2/cmdb/firewall/address"
        payload = {
            "name": name,
            "type": "ipmask",
            "subnet": f"{ip} 255.255.255.255"
        }
        r = requests.post(url, headers=self.headers, json=payload, verify=self.verify_ssl)
        return name, r.status_code, r.text

    def add_to_group(self, group, member):
        url = f"https://{self.host}/api/v2/cmdb/firewall/addrgrp/{group}"
        payload = {
            "member": [
                {"name": member}
            ]
        }
        r = requests.put(url, headers=self.headers, json=payload, verify=self.verify_ssl)
        return r.status_code, r.text
