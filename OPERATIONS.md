# Operacion diaria

## Servicios

Collector principal:

```bash
systemctl status fortigate-monitor
```

Reset diario de cuotas:

```bash
systemctl status fortigate-purge.timer
systemctl cat fortigate-purge.service
```

## Cron

El servidor ejecuta:

- `scripts/quota_manager.py` cada minuto.
- `scripts/daily_captive_reset.py` una vez al dia.

## Verificacion de cuotas

```bash
/opt/fortigate-monitor/venv/bin/python3 /opt/fortigate-monitor/scripts/quota_check.py
```

## Consola web

- `/health`: estado del appliance, servicios, FortiGate, DB y cuotas.
- `/diagnostics`: checklist de portabilidad para nuevos servidores o nuevos FortiGate.
- `/clients`: inventario diario de equipos.
- `/clients/<ip>`: detalle por equipo, servicios, destinos, politicas y aplicaciones.
- `/quotas`: centro operativo de cuotas, bloqueos y liberaciones.
- `/portal`: credenciales del portal cautivo y rotacion manual.
- `/settings`: configuracion editable con backup automatico de YAML.

## Exportaciones

Reporte diario de consumo por IP:

```text
/download/traffic-report.csv
```

Credenciales del portal cautivo:

```text
/download/captive-passwords
```

## Reset diario manual

Este comando libera bloqueos del FortiGate y limpia los contadores diarios. Usarlo solo cuando se quiera reiniciar el ciclo de consumo:

```bash
/opt/fortigate-monitor/venv/bin/python3 /opt/fortigate-monitor/scripts/daily_quota_reset.py
```

## Logs

```bash
journalctl -u fortigate-monitor -n 100 --no-pager
tail -n 100 /opt/fortigate-monitor/logs/quota_manager.log
tail -n 100 /opt/fortigate-monitor/logs/daily_captive_reset.log
```

## Configuracion relevante

```yaml
quota:
  limit_gb: 2
  blocked_group: BLOQUEADOS_2GB
```

El grupo debe existir en FortiGate y estar asociado a una politica que deniegue Internet.

Los cambios desde `/settings` generan un backup automatico en `/opt/fortigate-monitor/backups/` antes de reemplazar `config.yaml`.
