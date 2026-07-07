# Fases y versiones

Este documento resume la evolucion funcional del proyecto por fases. La premisa es que FortiGate Monitor pueda desplegarse en otros servidores y contra otros FortiGate sin tocar codigo.

## v1.7.0

### Fase 1 - Health Center

- Vista `/health` para revisar dashboard, collector, base SQLite, timer de reset, FortiGate y grupo de bloqueo.
- Formato horario local `America/Lima`.
- Validacion visual del estado general del appliance.

### Fase 2 - Clientes e iconografia

- Vista `/clients` con inventario diario por IP.
- Estados de consumo: normal, alerta, bloqueado y liberado.
- Iconos SVG integrados en la navegacion.

### Fase 3 - Auditoria operativa

- Tabla `audit_events`.
- Timeline `/events` para bloqueos, liberaciones, cambios de configuracion y rotaciones del portal.
- Eventos escritos por scripts y acciones manuales.

## v1.14.0

### Fase 4 - Detalle por cliente

- Vista `/clients/<ip>` para revisar un equipo especifico.
- Top de servicios, destinos, politicas y aplicaciones.
- Accion de liberacion directa si la IP esta bloqueada.

### Fase 5 - Centro de cuotas

- `/quotas` pasa a ser un centro operativo con resumen ejecutivo.
- Muestra equipos sobre limite, bloqueos activos, liberaciones y politica aplicada.
- Enlaces directos al detalle del cliente y a configuracion.

### Fase 6 - Portal cautivo profesional

- `/portal` muestra usuarios, ultima rotacion, longitud de password y estado del CSV.
- Accion manual para rotar todos los usuarios temporales.
- Auditoria de reset individual y rotacion masiva.

### Fase 7 - Configuracion avanzada desde UI

- `/settings` permite editar nombre/host FortiGate, SSH, zona horaria, longitud de password, cuota, grupo de bloqueo y redes monitoreadas.
- El API token no se expone desde la UI.
- Cada guardado crea backup automatico de `config.yaml`.

### Fase 8 - Diagnostico y portabilidad

- Nueva vista `/diagnostics`.
- Checklist de archivos, servicios, base de datos, API token, host y Address Group.
- Pensada para validar instalaciones en nuevos servidores.

### Fase 9 - Reportes/exportacion

- Exportacion `/download/traffic-report.csv`.
- CSV diario con consumo por IP, porcentaje de cuota, estado y ultima actividad.

### Fase 10 - Documentacion de release

- Version `1.14.0`.
- Documentacion de fases, release notes, changelog y operacion diaria actualizada.
- UI consolidada en estilo controlador dark/green.

## v1.14.1

### Parche - Inventario MAC

- Captura direcciones MAC desde campos FortiGate `srcmac`, `mastersrcmac` o `devicemac`.
- Agrega migracion automatica de SQLite para `srcmac` y `dstmac`.
- Muestra MAC en dashboard, clientes, detalle de cliente, centro de cuotas y CSV diario.
