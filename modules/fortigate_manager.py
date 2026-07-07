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
        self.timeout = config.get("timeout", 10)

    def create_address(self, ip):
        name = f"BLOCK_{ip}"
        url = f"https://{self.host}/api/v2/cmdb/firewall/address"
        payload = {
            "name": name,
            "type": "ipmask",
            "subnet": f"{ip} 255.255.255.255"
        }
        r = requests.post(
            url,
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl,
            timeout=self.timeout
        )
        return name, r.status_code, r.text

    def add_to_group(self, group, member):
        status, data = self.get_group(group)

        if status != 200:
            return status, data

        current = data["results"][0].get("member", [])

        if not any(item.get("name") == member for item in current):
            current.append({"name": member})

        url = f"https://{self.host}/api/v2/cmdb/firewall/addrgrp/{group}"
        payload = {
            "member": current
        }
        r = requests.put(
            url,
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl,
            timeout=self.timeout
        )
        return r.status_code, r.text


    def get_group(self, group):
        url = f"https://{self.host}/api/v2/cmdb/firewall/addrgrp/{group}"
        r = requests.get(
            url,
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=self.timeout
        )
        return r.status_code, r.json()

    def remove_from_group(self, group, member):
        status, data = self.get_group(group)

        if status != 200:
            return status, data

        current = data["results"][0].get("member", [])
        new_members = [m for m in current if m.get("name") != member]

        url = f"https://{self.host}/api/v2/cmdb/firewall/addrgrp/{group}"
        payload = {"member": new_members}

        r = requests.put(
            url,
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl,
            timeout=self.timeout
        )
        return r.status_code, r.text

    def delete_address(self, name):
        url = f"https://{self.host}/api/v2/cmdb/firewall/address/{name}"
        r = requests.delete(
            url,
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=self.timeout
        )
        return r.status_code, r.text
