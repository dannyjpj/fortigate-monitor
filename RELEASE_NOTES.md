# Release Notes

## FortiGate Monitor v1.14.4

Parche operativo para entregar una nueva cuota diaria a una IP especifica sin borrar historicos del dia.

### Incluye

- Boton `Restablecer cuota` en Centro de Cuotas y Detalle de Cliente.
- Tabla `quota_offsets` para tomar el consumo actual como punto cero.
- Recalculo de cuota en dashboard, health, clientes y quota manager usando consumo efectivo.
- Limpieza de offsets en el reset diario.
- CSV con `total_daily` y `quota_offset`.

## FortiGate Monitor v1.14.3

Parche visual para mejorar comportamiento responsive y limpiar etiquetas internas.

### Incluye

- Retiro de etiquetas `Fase X` en encabezados de categorias.
- Scroll horizontal controlado para tablas anchas.
- Modo tabla tipo tarjeta desde pantallas menores a 760px.

## FortiGate Monitor v1.14.2

Parche operativo para reflejar correctamente bloqueos de cuota y visualizar usuarios autenticados.

### Incluye

- Columna Usuario en vistas operativas y CSV.
- Captura de usuario desde campos FortiGate `user`, `srcuser`, `unauthuser` o `xauthuser`.
- Migracion automatica de SQLite para `auth_user`.
- Correccion del orden de commit en `quota_manager.py` para evitar que fallos de auditoria dejen la UI sin estado de bloqueo.

## FortiGate Monitor v1.14.1

Parche de inventario para mostrar direcciones MAC cuando FortiGate las envia en los logs.

### Incluye

- Captura de `srcmac`, `mastersrcmac` o `devicemac`.
- Migracion automatica de SQLite para columnas `srcmac` y `dstmac`.
- MAC visible en `/`, `/clients`, `/clients/<ip>` y `/quotas`.
- Campo `srcmac` agregado al CSV `/download/traffic-report.csv`.

## FortiGate Monitor v1.14.0

Esta version completa las fases 4 a 10 del rediseño operativo. El foco es convertir la aplicacion en una consola administrable y portable para otros servidores/FortiGate.

### Incluye

- Detalle por cliente con consumo, sesiones, servicios, destinos, politicas y aplicaciones.
- Centro de cuotas con resumen de bloqueos, liberaciones y equipos sobre limite.
- Portal cautivo con rotacion manual de todos los usuarios y visibilidad del CSV diario.
- Configuracion avanzada desde UI con backup automatico del YAML.
- Diagnostico para validar despliegues nuevos.
- Exportacion CSV diaria de trafico por cliente.
- Documentacion de fases y operacion.

### Versiones por fase

- `v1.7.0`: fases 1, 2 y 3.
- `v1.14.0`: fases 4, 5, 6, 7, 8, 9 y 10.

### Post-deploy recomendado

```bash
systemctl restart fortigate-dashboard
systemctl restart fortigate-monitor
systemctl status fortigate-dashboard --no-pager
systemctl status fortigate-monitor --no-pager
```

Luego validar:

- `/health`
- `/diagnostics`
- `/clients`
- `/quotas`
- `/portal`
