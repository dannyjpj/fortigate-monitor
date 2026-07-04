#!/usr/bin/env python3

CSV="/opt/fortigate-monitor/data/captive_passwords_today.csv"
OUT="/opt/fortigate-monitor/data/fortigate_reset_passwords.cli"

with open(CSV) as f, open(OUT, "w") as out:
    out.write("config vdom\n")
    out.write("edit root\n")
    out.write("config user local\n")

    next(f)

    for line in f:
        fecha, user, password = line.strip().split(",")

        out.write(f'    edit "{user}"\n')
        out.write(f'        set passwd "{password}"\n')
        out.write("    next\n")

    out.write("end\n")

print(OUT)
