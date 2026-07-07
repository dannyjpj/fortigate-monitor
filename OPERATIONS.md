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
