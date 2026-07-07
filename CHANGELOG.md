# Changelog

## 1.14.4 - Restablecimiento manual de cuota

- Agrega boton `Restablecer cuota` junto a `Liberar`.
- Implementa `quota_offsets` para reiniciar el contador de una IP sin borrar el trafico diario.
- El consumo previo pasa a ser el punto cero y la IP recibe una cuota completa nueva.
- El bloqueo automatico vuelve a aplicar cuando la IP consume nuevamente el limite configurado.
- El reset diario limpia tambien `quota_offsets`.
- El CSV agrega total diario y offset de cuota.

## 1.14.3 - Limpieza visual y tablas responsive

- Quita etiquetas visibles `Fase X` de las categorias del dashboard.
- Agrega scroll horizontal controlado a tablas anchas en desktop/tablet.
- Adelanta el modo tarjeta responsive de tablas para pantallas menores a 760px.
- Evita cortes visuales en Clientes al mostrar IP, MAC, Usuario, Nombre y consumo.

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
