# Changelog

## 1.14.2 - Usuario autenticado y cuota robusta

- Captura usuario autenticado desde logs FortiGate (`user`, `srcuser`, `unauthuser`, `xauthuser`).
- Agrega columna `auth_user` a SQLite con migracion automatica.
- Muestra Usuario en dashboard, clientes, detalle de cliente, cuotas y CSV.
- Corrige `quota_manager.py` para guardar `quota_status` antes de auditar, evitando que `database is locked` oculte bloqueos ya aplicados.
- Actualiza consumo de una IP ya bloqueada sin volver a crear objetos FortiGate.

## 1.14.1 - Inventario MAC

- Captura `srcmac`, `mastersrcmac` o `devicemac` desde logs FortiGate cuando esten disponibles.
- Agrega columnas `srcmac` y `dstmac` a SQLite con migracion automatica.
- Muestra MAC en dashboard, clientes, detalle de cliente y centro de cuotas.
- Incluye MAC en la exportacion CSV diaria de trafico.

## 1.14.0 - Fases 4 a 10

- Agrega detalle por cliente en `/clients/<ip>`.
- Rediseña `/quotas` como centro de cuotas con resumen ejecutivo, equipos sobre limite y acciones.
- Profesionaliza `/portal` con metricas, rotacion manual masiva y auditoria.
- Amplia `/settings` para parametrizar FortiGate, SSH, zona horaria y passwords del portal.
- Agrega `/diagnostics` para validar portabilidad en nuevos servidores.
- Agrega exportacion CSV diaria en `/download/traffic-report.csv`.
- Documenta fases, versiones y operacion.

## 1.7.0 - Fases 1 a 3

- Agrega Health Center.
- Agrega inventario de clientes con estados de cuota.
- Agrega iconografia SVG de navegacion.
- Agrega auditoria operativa.
- Corrige bloqueo por cuota preservando miembros existentes del Address Group.
- Agrega reset diario de cuotas y zona horaria `America/Lima`.
