# Arquitectura de red

## Diseño: Collapsed Core

La arquitectura Collapsed Core fusiona las capas de core y distribución en dos switches L3,
eliminando la capa de distribución independiente. Es la elección habitual en empresas
de tamaño medio: ofrece alta disponibilidad con menos hardware y menor complejidad operativa.

```
                    FortiGate FG-100D
                    192.168.127.200
                    FortiOS v6.2.16
                          │
               enlace tránsito VLAN 150
               172.16.150.0/29
                    │         │
             172.16.150.2   172.16.150.3
              ┌──────┐       ┌──────┐
              │ CD-1 │═══════│ CD-2 │    trunk inter-cores
              │ 3850 │       │ 3850 │
              └──────┘       └──────┘
              HSRP activo    HSRP standby
              prioridad 110  prioridad 100
                  │                 │
            ┌─────┘                 └─────┐
          SW-A1                         SW-A2
        Catalyst 2960                Catalyst 2960
        (usuarios/oficina)           (infraestructura)
        Fa0/1-5   → VLAN7            Fa0/13 → Proxmox (trunk)
        Fa0/6-10  → VLAN40
        Fa0/11-14 → VLAN20
        Fa0/17    → WAP150 (trunk 60,70,99)
```

## HSRP — Redundancia de gateway

HSRP garantiza que si un core cae, los equipos de la red no pierden su gateway.
Los hosts apuntan siempre a la IP virtual (VIP), que en condiciones normales
responde CD-1 y en caso de fallo la toma CD-2.

**Object tracking:** CD-1 monitoriza su uplink físico hacia el FortiGate (Gi1/0/24).
Si ese enlace cae, CD-1 reduce su prioridad a 90 automáticamente,
por debajo de los 100 de CD-2, que asume el rol activo sin intervención manual.

## OSPF — Routing dinámico

OSPF área 0 entre FortiGate (router-id 3.3.3.3), CD-1 (1.1.1.1) y CD-2 (2.2.2.2).

El FortiGate redistribuye sus redes conectadas y propaga la ruta por defecto hacia internet
(`default-information-originate always`). Los cores aprenden automáticamente
cómo llegar a la DMZ (192.168.100.0/24) sin rutas estáticas manuales.

Cuando ambos cores están activos, el tráfico hacia internet se balancea entre
los dos caminos (ECMP, cost 101 en ambos).

## VLANs

El tráfico está segmentado en 10 VLANs con propósito específico:

| VLAN | Nombre | Subred | Gateway HSRP | DHCP |
|------|--------|--------|--------------|------|
| 7 | Marketing | 10.0.7.0/24 | 10.0.7.1 | Sí |
| 10 | Datos Críticos | 10.0.10.0/24 | 10.0.10.1 | No (estática) |
| 20 | VoIP | 10.0.20.0/24 | 10.0.20.1 | Sí + opción 150 |
| 40 | Ventas | 10.0.40.0/24 | 10.0.40.1 | Sí |
| 60 | WiFi Empleados | 10.0.60.0/24 | 10.0.60.1 | Sí |
| 70 | WiFi Invitados | 10.0.70.0/24 | 10.0.70.1 | Sí |
| 87 | Servidores LAN | 10.0.87.0/24 | 10.0.87.1 | No (estática) |
| 99 | Gestión | 10.0.99.0/24 | 10.0.99.1 | No (estática) |
| 100 | DMZ | 192.168.100.0/24 | 192.168.100.1 | No (estática) |
| 150 | Tránsito | 172.16.150.0/29 | — | No |

La VLAN 10 (base de datos) no tiene salida a internet ni a otras VLANs de usuario.
Solo la webapp (VLAN 100) y el servidor de correo (VLAN 87) pueden acceder al puerto 3306,
controlado tanto por políticas FortiGate como por iptables en la propia VM.

## FortiGate FG-100D

El FortiGate es el único punto de salida a internet y el controlador de tráfico entre VLANs.

**Interfaces activas:**

| Interfaz | IP | Rol |
|----------|-----|-----|
| wan1 | 192.168.127.200/24 | WAN — red del instituto (internet) |
| lan | 172.16.150.1/29 | Tránsito hacia cores — OSPF |
| lan.100 | 192.168.100.1/24 | Gateway DMZ — subinterfaz 802.1Q |

La DMZ se implementa como subinterfaz 802.1Q sobre el puerto físico `lan`,
etiquetada con VLAN 100. Esto permite al FortiGate ser el gateway de la DMZ
sin necesitar un puerto físico adicional.

**VIPs (NAT entrante):**

| Nombre | Externo | Interno |
|--------|---------|---------|
| VIP_WebServer | :80 | VM101:80 |
| VIP_WebServer_HTTPS | :443 | VM101:443 |
| VIP-Proxmox-8006 | :8006 | Proxmox:8006 |
| VIP_WireGuard | :51820/UDP | VM105:51820 |

## VTPv3

Los switches usan VTPv3 para sincronizar la base de datos de VLANs automáticamente.
CD-1 es el servidor primario y propaga las VLANs a CD-2, SW-A1 y SW-A2.
Cualquier cambio en la base de datos de VLANs se hace únicamente en CD-1.
