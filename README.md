# FortiGate Monitor

Sistema de monitoreo y administración para FortiGate orientado a entornos internos.

## Funcionalidades

### Dashboard

- Resumen de tráfico
- Top IPs
- Top servicios
- Top destinos
- Consumo por red
- Actualización automática

### Control de cuotas

- Visualización de equipos bloqueados
- Liberación de cuotas desde la interfaz
- Sincronización con FortiGate

### Portal cautivo

- Visualización de usuarios visita
- Generación automática de contraseñas
- Reset individual de contraseña
- Descarga de credenciales en CSV
- Reset diario automático mediante cron

### Seguridad

- Login de administrador
- Contraseñas protegidas mediante hash (Werkzeug/Scrypt)
- Gestión de sesiones
- Cierre de sesión
- HTTPS mediante certificado SSL autofirmado
- Acceso destinado únicamente a administradores internos

## Arquitectura

```
Flask
│
├── Dashboard
├── Portal Cautivo
├── Control de Cuotas
└── API FortiGate
```

## Estructura

```
fortigate-monitor/
├── dashboard/
├── modules/
├── scripts/
├── data/
├── logs/
├── certs/
├── config.yaml
└── VERSION
```

## Requisitos

- Python 3.9+
- Flask
- SQLite
- FortiGate API
- Acceso SSH al FortiGate mediante llave ED25519

## Seguridad

- HTTPS habilitado
- Certificados locales
- Contraseñas hasheadas
- Sesiones autenticadas

## Versión

v1.6.0
