# Servicios desplegados

## Windows Server 2022 — Active Directory, DHCP, DNS

**VM102 · 10.0.87.10 · VLAN 87**

Controlador de dominio del entorno. El dominio `exoticmotors.proven` centraliza
la autenticación de todos los servicios internos que requieren identidad corporativa:
webmail, telefonía y acceso a carpetas de red.

**Active Directory:**
- Dominio: `exoticmotors.proven` (modo funcional Windows 2016)
- OUs: Empleados → Marketing / Ventas / IT · Servidores
- 4 usuarios corporativos con UPN adicional para Entra Connect

**DHCP:**
Cinco scopes activos con relay configurado en CD-1 y CD-2 (`ip helper-address 10.0.87.10`):

| Scope | VLAN | Rango |
|-------|------|-------|
| Marketing | 7 | 10.0.7.10–200 |
| VoIP | 20 | 10.0.20.11–200 |
| Ventas | 40 | 10.0.40.10–200 |
| WiFi Empleados | 60 | 10.0.60.10–200 |
| WiFi Invitados | 70 | 10.0.70.10–200 |

La VLAN de VoIP incluye la opción DHCP 150 (TFTP) apuntando al servidor PBX,
necesaria para el aprovisionamiento de terminales IP.

**DNS:**
Zona primaria `exoticmotors.proven` con registros A para todos los servicios internos.
Forwarder externo: 8.8.8.8.

**GPOs:**
- Carpetas compartidas por departamento mapeadas automáticamente (Z:)
- Unidad de red personal por usuario (H:)

---

## Servidor de correo — Postfix + Dovecot + Roundcube

**VM104 · 10.0.87.11 · VLAN 87**

Stack de correo corporativo completo con autenticación integrada en Active Directory.

```
Usuario → HTTPS:443 → Nginx → Roundcube (PHP 8.3)
                                    │
                         IMAP:143 (Dovecot) → Maildir /srv/vmail/
                         SMTP:587 (Postfix submission + SASL)
                                    │
                         LDAP auth → AD 10.0.87.10
                         BD sesiones → MariaDB roundcubedb
```

**Flujo de un email entrante:**
```
Postfix :25 recibe → milter llama Rspamd → Rspamd llama ClamAV (socket) → entrega Dovecot LMTP
```

- **Autenticación:** Dovecot hace bind directo al AD con el UPN del usuario
  (`usuario@exoticmotors.proven`). No se necesita cuenta de servicio LDAP.
- **Antivirus/Antispam:** ClamAV (firmas de virus) + Rspamd (scoring de spam) como milter.
  Los mensajes maliciosos se rechazan antes de la entrega.
- **Webmail:** Roundcube en HTTPS con certificado autofirmado (válido 10 años).

---

## PBX — 3CX SBC v20

**VM103 · 10.0.20.10 · VLAN 20**

La VM ejecuta un Session Border Controller que actúa como proxy local
hacia la instancia 3CX en la nube (`1229.3cx.cloud`).

```
App móvil 3CX / Teléfono IP
        │ SIP:5060
   SBC (10.0.20.10)
        │ TLS:5090 (túnel cifrado)
   1229.3cx.cloud
        │
   Destino de la llamada
```

- 5 extensiones configuradas (17910–17914)
- Grupo de timbrado "Compras y Ventas" (extensión 17960)
- Puertos RTP 20000–20063 para audio

---

## Base de datos — MariaDB

**VM100 · 10.0.10.10 · VLAN 10**

MariaDB aislado en su propia VLAN. El acceso al puerto 3306 está restringido
a nivel de iptables: solo acepta conexiones desde la webapp (192.168.100.10)
y el servidor de correo (10.0.87.11).

Bases de datos activas:

| Base de datos | Usuario | Acceso desde |
|--------------|---------|--------------|
| concesionario | app_web | VM101 (webapp) |
| roundcubedb | roundcube | VM104 (webmail) |

El bind está configurado en `0.0.0.0` con `skip-name-resolve` activo.
La seguridad perimetral la gestiona iptables, no la configuración de MariaDB.
