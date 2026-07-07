# Arquitectura operativa

FortiGate Monitor compensa la falta de cuotas nativas por servicio en FortiGate mediante automatizacion externa.

## Flujo principal

1. FortiGate envia logs de trafico al servidor.
2. `collector.py` sigue el archivo configurado en `general.log_file`.
3. `modules.parser.FortigateParser` extrae campos como `srcip`, `dstip`, `service`, `sentbyte` y `rcvdbyte`.
4. `modules.networks.NetworkClassifier` acepta solo IPs que pertenecen a las redes configuradas.
5. `modules.database.Database` guarda el trafico diario en SQLite.
6. `scripts/quota_manager.py` corre cada minuto desde cron.
7. Si una IP supera `quota.limit_gb`, crea un address object `BLOCK_<ip>` en FortiGate y lo agrega al grupo `quota.blocked_group`.
8. Una politica del FortiGate debe negar Internet al grupo configurado.

## Reset diario

El timer `fortigate-purge.timer` ejecuta `scripts/daily_quota_reset.py`.

Ese script:

- Lee bloqueos activos en `quota_status`.
- Quita cada objeto del grupo de bloqueo.
- Elimina el address object `BLOCK_<ip>`.
- Limpia `traffic` y `quota_status`.

El proyecto esta pensado para operar con datos diarios, sin historico permanente de consumo.

## Portal cautivo

`scripts/daily_captive_reset.py` genera passwords nuevos para los usuarios definidos en `captive_portal.users`, actualiza el CSV diario y aplica los cambios por SSH al FortiGate.

El dashboard permite consultar esas credenciales y resetear usuarios individuales.
