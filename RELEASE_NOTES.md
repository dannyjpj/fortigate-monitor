# Release Notes

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
