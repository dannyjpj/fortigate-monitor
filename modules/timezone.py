from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


DEFAULT_TIMEZONE = "America/Lima"
CONFIG_FILE = Path("/opt/fortigate-monitor/config.yaml")


def configured_timezone():
    if yaml is None:
        return DEFAULT_TIMEZONE

    try:
        cfg = yaml.safe_load(CONFIG_FILE.read_text()) or {}
        return cfg.get("general", {}).get("timezone", DEFAULT_TIMEZONE)
    except Exception:
        return DEFAULT_TIMEZONE


def get_timezone(name=None):
    name = name or configured_timezone()

    if ZoneInfo is None:
        return timezone(timedelta(hours=-5))

    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def local_now(name=None):
    return datetime.now(get_timezone(name))


def local_date(name=None):
    return local_now(name).strftime("%Y-%m-%d")


def local_timestamp(name=None):
    return local_now(name).strftime("%Y-%m-%d %H:%M:%S")


def local_stamp(name=None):
    return local_now(name).strftime("%Y%m%d-%H%M%S")
