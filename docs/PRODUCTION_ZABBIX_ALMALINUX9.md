# Despliegue en produccion con Zabbix y AlmaLinux/Rocky 9

Esta guia resume el despliegue validado en produccion cuando el servidor ya ejecuta Zabbix sobre Apache y Zabbix conserva la prioridad de los puertos `80` y `443`.

## Arquitectura

```text
FortiGate
  ├─ API HTTPS -> FortiGate Monitor
  ├─ SSH con llave publica -> reset de usuarios del portal cautivo
  └─ Syslog UDP 514 -> rsyslog -> /var/log/fortigate.log

Apache/Zabbix
  ├─ /zabbix/       -> Zabbix
  └─ /fortigate/   -> reverse proxy a 127.0.0.1:5000

FortiGate Monitor
  ├─ fortigate-dashboard.service -> Gunicorn/Flask
  ├─ fortigate-monitor.service   -> collector.py
  └─ fortigate-purge.timer       -> reset diario de cuotas
```

## Apache bajo `/fortigate/`

Archivo recomendado:

```apache
RedirectMatch 302 ^/fortigate$ /fortigate/

<Location /fortigate/>
    RequestHeader set X-Forwarded-Prefix "/fortigate"
    RequestHeader set X-Forwarded-Proto "http"

    ProxyPreserveHost On
    ProxyPass http://127.0.0.1:5000/
    ProxyPassReverse http://127.0.0.1:5000/
    ProxyPassReverseCookiePath / /fortigate/
</Location>
```

Validar:

```bash
sudo httpd -t
sudo systemctl reload httpd
curl -i http://127.0.0.1:5000/login
curl -i http://SERVIDOR/fortigate/login
```

## Base de datos

`config.yaml` debe apuntar a la base usada por el collector:

```yaml
general:
  database: /opt/fortigate-monitor/data/traffic.db
```

Validar:

```bash
sudo sqlite3 /opt/fortigate-monitor/data/traffic.db ".tables"
```

Deben existir:

```text
traffic
quota_status
quota_offsets
audit_events
```

## Syslog y collector

El collector lee:

```text
/var/log/fortigate.log
```

Abrir firewall:

```bash
sudo firewall-cmd --add-port=514/udp --permanent
sudo firewall-cmd --reload
```

Configurar rsyslog:

```bash
sudo tee /etc/rsyslog.d/10-fortigate.conf >/dev/null <<'EOF'
module(load="imudp")

ruleset(name="fortigate_remote") {
    action(type="omfile" file="/var/log/fortigate.log")
    stop
}

input(type="imudp" port="514" ruleset="fortigate_remote")
EOF

sudo touch /var/log/fortigate.log
sudo chmod 640 /var/log/fortigate.log
sudo systemctl restart rsyslog
```

Validar entrada:

```bash
sudo ss -lunp | grep ':514'
sudo tcpdump -ni any host IP_FORTIGATE and port 514
sudo tail -f /var/log/fortigate.log
```

Reiniciar collector despues de confirmar que el archivo recibe logs:

```bash
sudo systemctl restart fortigate-monitor
sudo journalctl -u fortigate-monitor -f
```

Validar SQLite:

```bash
sudo sqlite3 /opt/fortigate-monitor/data/traffic.db \
"select fecha,hora,network,srcip,srcmac,auth_user,sentbyte+rcvdbyte from traffic order by id desc limit 10;"
```

## FortiGate

Enviar syslog al servidor:

```text
config log syslogd setting
    set status enable
    set server "IP_SERVIDOR"
    set mode udp
    set port 514
    set facility local7
end

config log syslogd filter
    set forward-traffic enable
    set local-traffic enable
    set severity information
end
```

Las politicas que se quieran medir deben registrar sesiones:

```text
config firewall policy
    edit ID_POLITICA
        set logtraffic all
    next
end
```

## SSH para portal cautivo

Crear llave en el servidor:

```bash
sudo ssh-keygen -t ed25519 \
  -f /opt/fortigate-monitor/certs/fortigate_ssh_key \
  -C "root@fortigate-monitor-prod" \
  -N ""
```

Registrar la publica en FortiGate:

```text
config system admin
    edit "fg-monitor"
        set accprofile "super_admin"
        set vdom "root"
        set ssh-public-key1 "ssh-ed25519 AAAA... root@fortigate-monitor-prod"
    next
end
```

El script actual espera la llave en:

```text
/root/.ssh/fortigate_monitor
```

Preparar:

```bash
sudo mkdir -p /root/.ssh
sudo cp /opt/fortigate-monitor/certs/fortigate_ssh_key /root/.ssh/fortigate_monitor
sudo chmod 600 /root/.ssh/fortigate_monitor
```

Validar:

```bash
sudo ssh -i /root/.ssh/fortigate_monitor -p 22 -o IdentitiesOnly=yes fg-monitor@IP_FORTIGATE
```

## Reset diario

Crear timer para las `00:01 America/Lima` usando `05:01 UTC`:

```bash
sudo systemctl enable --now fortigate-purge.timer
sudo systemctl status fortigate-purge.timer --no-pager
sudo systemctl list-timers | grep fortigate
```

## Checklist final

- Zabbix conserva `/zabbix/`, `80` y `443`.
- FortiGate Monitor responde en `/fortigate/`.
- `/healthz` responde localmente.
- API FortiGate marca OK en Diagnostics.
- SSH con llave entra al FortiGate.
- `/var/log/fortigate.log` recibe logs.
- `traffic.db` recibe registros.
- `fortigate-dashboard`, `fortigate-monitor` y `fortigate-purge.timer` estan activos.
