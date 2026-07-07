# Seguridad

## Secretos

`config.yaml` contiene secretos operativos como `dashboard.secret_key`, hashes de usuarios y token API del FortiGate. No debe subirse a repositorios publicos.

Recomendaciones:

- Mantener permisos restrictivos: `chmod 600 /opt/fortigate-monitor/config.yaml`.
- Rotar el token API si se comparte el archivo por error.
- Usar un token de FortiGate con permisos minimos para address objects y address groups.

## SSH

Los scripts usan llave privada en `/root/.ssh/fortigate_monitor`.

Recomendaciones:

- Proteger la llave con permisos `600`.
- Limitar el usuario SSH del FortiGate a las acciones necesarias.
- Revisar logs si falla el reset diario de portal cautivo.

## Dashboard

El dashboard debe exponerse solo en red administrativa o detras de VPN.

Recomendaciones:

- Usar HTTPS.
- Cambiar `dashboard.secret_key` en cada instalacion.
- Evitar contrasenas compartidas.
- Habilitar auditoria de acciones administrativas en una version futura.
