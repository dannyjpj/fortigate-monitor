import shlex


class FortigateParser:

    def parse(self, line):

        try:
            tokens = shlex.split(line)
        except Exception:
            return None

        data = {}

        for token in tokens:

            if "=" not in token:
                continue

            key, value = token.split("=", 1)
            data[key] = value

        return {
            "fecha": data.get("date"),
            "hora": data.get("time"),
            "srcip": data.get("srcip"),
            "srcname": data.get("srcname"),
            "dstip": data.get("dstip"),
            "policyid": int(data.get("policyid", 0)),
            "policyname": data.get("policyname"),
            "service": data.get("service"),
            "app": data.get("app"),
            "action": data.get("action"),
            "sentbyte": int(data.get("sentbyte", 0)),
            "rcvdbyte": int(data.get("rcvdbyte", 0)),
            "duration": int(data.get("duration", 0))
        }
