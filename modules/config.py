import yaml

CONFIG_FILE = "/opt/fortigate-monitor/config.yaml"


class Config:

    def __init__(self):

        with open(CONFIG_FILE, "r") as f:
            self.cfg = yaml.safe_load(f)

    def get(self):
        return self.cfg
