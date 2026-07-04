import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FortiGateAPI:

    def __init__(self, config):
        self.host = config["host"]
        self.token = config["api_token"]
        self.vdom = config.get("vdom", "root")
        self.verify_ssl = config.get("verify_ssl", False)

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def update_local_user_password(self, username, password):
        url = (
            f"https://{self.host}"
            f"/api/v2/cmdb/user/local/{username}"
        )

        payload = {
            "passwd": password
        }

        response = requests.put(
            url,
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl,
            timeout=10
        )

        return response.status_code, response.text
