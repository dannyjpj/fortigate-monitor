#!/usr/bin/env python3

from modules.reports import Reports
from modules.config import Config


def bytes_to_human(num):

    for unit in ["B", "KB", "MB", "GB", "TB"]:

        if num < 1024:
            return f"{num:.2f} {unit}"

        num /= 1024

    return f"{num:.2f} PB"


cfg = Config().get()

print("=" * 60)
print(" FortiGate Traffic Report")
print("=" * 60)
print(f"Firewall : {cfg['fortigate']['name']}")
print("=" * 60)

r = Reports()

print("\nTOP IPS")
print("-" * 60)

for row in r.top_ips():

    print(
        f"{row['srcip']:<15}"
        f"{row['srcname']:<25}"
        f"{bytes_to_human(row['bytes']):>12}"
    )

print("\nTOP SERVICIOS")
print("-" * 60)

for row in r.top_services():

    print(
        f"{row['service']:<20}"
        f"{bytes_to_human(row['bytes']):>12}"
        f"   ({row['conexiones']} conexiones)"
    )

print("\nTOP POLITICAS")
print("-" * 60)

for row in r.top_policies():

    print(
        f"{row['policyname']:<35}"
        f"{bytes_to_human(row['bytes']):>12}"
    )

print("\nTOP DESTINOS")
print("-" * 60)

for row in r.top_destinations():

    print(
        f"{row['dstip']:<18}"
        f"{bytes_to_human(row['bytes']):>12}"
    )

print("\nTRAFICO POR RED")
print("-" * 60)

for row in r.traffic_by_network():

    print(
        f"{row['network']:<20}"
        f"{bytes_to_human(row['bytes']):>12}"
    )

r.close()

print("\n" + "=" * 60)
