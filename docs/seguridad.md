# Diseño de seguridad

## Principios aplicados

El diseño de seguridad parte de dos premisas:

1. **Mínimo privilegio:** cada servicio solo puede comunicarse con lo estrictamente necesario.
2. **Defensa en profundidad:** las restricciones se aplican en varias capas — FortiGate, iptables en las VMs, y segmentación VLAN en la red.

---

## Segmentación de red

Las 10 VLANs no son solo organizativas — tienen consecuencias reales de seguridad:

- **VLAN 10 (Base de datos):** completamente aislada. Ningún equipo de usuario puede alcanzarla. Solo la webapp y el servidor de correo tienen acceso al puerto 3306, y eso lo controla FortiGate.
- **VLAN 70 (WiFi invitados):** política de denegación hacia toda la red interna. Internet sí, LAN no.
- **VLAN 100 (DMZ):** la webapp vive aquí. Tiene acceso solo a los servicios que necesita (BD y correo). El resto de la LAN está bloqueado por política explícita.

---

## DMZ lógica 802.1Q

La DMZ no es un puerto físico separado del FortiGate, sino una subinterfaz 802.1Q (`lan.100`)
etiquetada con VLAN 100 sobre el mismo enlace físico que el tránsito de routing.

Esto permite un control granular del tráfico sin hardware adicional:
el FortiGate decide qué puede salir de la DMZ y hacia dónde,
evaluando cada flujo contra la lista de políticas.

---

## Políticas de firewall — filosofía

El tráfico entrante desde internet se acepta solo para servicios con VIP configurado.
Todo lo demás se descarta en el FortiGate antes de entrar a la red.

El tráfico saliente de la DMZ sigue el principio de lista blanca:

```
DMZ → BD (MySQL:3306)         ← permitido explícitamente
DMZ → Mail (SMTP:25)          ← permitido explícitamente (debe ir ANTES del DENY)
DMZ → resto de la LAN         ← DENEGADO por política explícita
DMZ → internet (EC2)          ← permitido con NAT para el túnel WireGuard
```

El orden de evaluación de las políticas es crítico. La excepción SMTP
debe estar posicionada antes del DENY general, porque el servidor de correo
forma parte del bloque de IPs "LAN interna" que la política general deniega.

---

## VPN sobre internet

En lugar de exponer puertos directamente al exterior, toda la conectividad
remota pasa por túneles cifrados:

- **Administradores:** WireGuard VPN (VM105) — acceso a toda la red interna tras autenticación
- **Usuarios públicos:** tráfico a través del relay EC2 → WireGuard → VM101 (HTTPS termina en EC2)

La IP pública del FortiGate no tiene puertos abiertos a internet excepto los necesarios
para los servicios expuestos (web pública y VPN corporativa).

---

## Gestión de secretos en la webapp

La webapp no almacena credenciales en código. Las conexiones a base de datos
y la clave secreta de Flask se cargan desde variables de entorno en producción.

Ver [`.env.example`](../webapp/.env.example) para las variables requeridas.
