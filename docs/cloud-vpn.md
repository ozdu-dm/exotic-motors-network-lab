# Cloud y VPN

## Exposición pública en internet — AWS EC2 + WireGuard

El instituto no permite port forwarding desde internet hacia la red interna.
La solución fue desplegar un servidor EC2 en AWS como punto de entrada público,
conectado a la red del lab mediante un túnel WireGuard.

### Arquitectura

```
Usuario en internet
       │  DNS: exoticmotors.duckdns.org → 35.169.27.141
       │  HTTPS (Let's Encrypt — cert en EC2)
       ▼
EC2 Ubuntu 24.04 — Nginx
       │  proxy_pass http://10.8.0.2:80
       │  (HTTP dentro del túnel, cifrado por WireGuard)
       │
WireGuard túnel cifrado
10.8.0.1 (EC2) ↔ 10.8.0.2 (VM101)
       │
VM101 — Nginx:80 → Gunicorn:5000 → Flask
```

El tráfico viaja en HTTP dentro del túnel WireGuard. Aunque el protocolo de capa 7
es HTTP, el transporte está cifrado por WireGuard (ChaCha20Poly1305).
El certificado HTTPS termina en EC2 porque es allí donde vive el dominio público.

### Por qué Nginx en VM101 no redirige HTTP→HTTPS

El proxy en EC2 accede a VM101 por HTTP (puerto 80). Si VM101 redirigiera todo
el tráfico HTTP a HTTPS, EC2 recibiría un 301 y entraría en bucle al no poder
completar el HTTPS internamente. Los dos bloques de Nginx en VM101 tienen propósitos distintos:

- **Puerto 80:** para el relay de EC2 — proxy directo a Gunicorn, sin redirección
- **Puerto 443:** para acceso desde la red interna — Nginx con certificado autofirmado

### Seguridad en EC2

Security group con cuatro reglas únicas:

| Puerto | Protocolo | Descripción |
|--------|-----------|-------------|
| 22/TCP | SSH | Administración |
| 80/TCP | HTTP | Redirect a HTTPS |
| 443/TCP | HTTPS | Aplicación web pública |
| 51820/UDP | WireGuard | Túnel con VM101 |

---

## WireGuard VPN corporativa — VM105

Además del túnel hacia EC2, el lab tiene un servidor WireGuard interno
para acceso remoto de administradores a toda la red interna.

**VM105 · 10.0.87.12 · VLAN 87**

```
Administrador remoto
       │  UDP:51820
FortiGate VIP_WireGuard (192.168.127.200:51820) → VM105:51820
       │
Red VPN 10.0.200.0/24
   10.0.200.1 (servidor VM105)
   10.0.200.2 (vpn_admin)
   10.0.200.3 (vpn_jgarcia)
       │
AllowedIPs: 10.0.0.0/8 + 192.168.100.0/24
→ Acceso completo a todas las VLANs internas
```

El servidor hace masquerade del tráfico VPN hacia la red interna.
`ip_forward` está habilitado via `/etc/sysctl.d/99-wireguard.conf`
para garantizar persistencia en reinicios.

---

## Microsoft Entra ID Connect

### Objetivo

Sincronizar las identidades del Active Directory local con Azure Entra ID,
permitiendo gestión centralizada de usuarios y preparación para SSO y MFA.

### Estado implementado

- Entra Connect v2.4.129.0 instalado en VM102, servicio ADSync en estado Running
- Modo: Password Hash Synchronization (PHS)
- Tenant: `Exoticmotors2026gmail.onmicrosoft.com`

### Configuración en Azure

4 usuarios creados con UPNs que coinciden con el AD local:

| UPN Azure | Rol directorio |
|-----------|---------------|
| oducuara@Exoticmotors2026gmail.onmicrosoft.com | Administrador de grupos |
| jcarlos@Exoticmotors2026gmail.onmicrosoft.com | Lector global |
| jnieto@Exoticmotors2026gmail.onmicrosoft.com | Administrador de usuarios |
| ggonzalez@Exoticmotors2026gmail.onmicrosoft.com | — |

Grupos de seguridad: Marketing, Ventas, IT.

### Prerrequisito de red

La política FortiGate `LAN_to_WAN_Internet` incluye la subred de servidores (VLAN 87)
en el grupo de origen, lo que permite a VM102 alcanzar los endpoints de Azure
(TCP 443) sin configuración adicional.
