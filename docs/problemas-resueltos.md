# Problemas resueltos durante el proyecto

Incidencias reales encontradas durante el despliegue, con causa raíz y solución aplicada.

---

## Red y FortiGate

### P-01 — La webapp no podía enviar emails al servidor de correo

**Síntoma:** El botón de asignar visita no enviaba notificación. Sin error visible, timeout silencioso.

**Causa:** La política de firewall que permitía SMTP desde la DMZ hacia el servidor de correo
estaba colocada después del DENY general DMZ→LAN. Como el servidor de correo (10.0.87.11)
forma parte del grupo `GRP_LAN_All`, la regla de denegación se evaluaba primero.

**Solución:** Mover la política `DMZ_Web_to_Mail_SMTP` a una posición anterior al DENY general.
El orden de evaluación de políticas en FortiGate es secuencial — la primera que coincide gana.

---

### P-02 — WireGuard VM105: los clientes conectaban pero sin routing

**Síntoma:** El cliente VPN establecía handshake correctamente pero no podía hacer ping
a ninguna IP interna.

**Causa:** `net.ipv4.ip_forward` estaba en 0 en runtime pese a aparecer correctamente
en `/etc/sysctl.conf`. El valor del archivo de configuración no se había aplicado al kernel activo.

**Solución:** Activar en runtime con `sysctl -w net.ipv4.ip_forward=1` y crear
`/etc/sysctl.d/99-wireguard.conf` para garantizar persistencia en reinicios
(más robusto que depender solo de `sysctl.conf`).

---

### P-03 — VIP UDP no creado mediante API REST en FortiGate

**Síntoma:** Script de automatización fallaba al intentar crear el VIP de WireGuard (UDP 51820).

**Causa:** FortiOS v6.2.16 no soporta la creación de VIPs con protocolo UDP a través de la REST API.

**Solución:** Crear el VIP directamente mediante SSH CLI o la interfaz web del FortiGate.

---

## Servidor de correo (VM104)

### P-04 — Roundcube devuelve "Login failed" con credenciales correctas

**Causa:** Dovecot intentaba hacer bind en LDAP usando `CN=Administrador` como cuenta
de servicio, lo que genera "Operations error" en Active Directory.

**Solución:** Cambiar a `auth_bind_userdn = %u` — bind directo con el UPN del usuario
(`oducuara@exoticmotors.proven`). Así Dovecot no necesita una cuenta de servicio LDAP.

---

### P-05 — Crash del proceso de autenticación de Dovecot

**Síntoma:** El servicio de auth de Dovecot caía al arrancar con error de configuración.

**Causa:** Se habían añadido parámetros `timeout`, `connect_timeout` e `idle_timeout`
en `dovecot-ldap.conf.ext` consultando documentación desactualizada.
Estos parámetros no existen en la versión de Dovecot instalada.

**Solución:** Eliminar los tres parámetros. Dovecot funciona con los timeouts por defecto.

---

### P-06 — smtplib de Flask cortaba la conexión SMTP antes de recibir respuesta

**Síntoma:** La función de notificación al vendedor fallaba con `SMTPServerDisconnected`.

**Causa:** El timeout por defecto de smtplib era 5 segundos. El pipeline
Postfix → Rspamd → ClamAV tarda entre 3 y 5 segundos en procesar cada mensaje.

**Solución:** Aumentar el timeout a 30 segundos: `smtplib.SMTP(host, port, timeout=30)`.

---

## Aplicación web (VM101)

### P-07 — La web no cargaba desde internet vía dominio público

**Síntoma:** `exoticmotors.duckdns.org` no respondía aunque el túnel WireGuard con EC2
estaba activo y el handshake era correcto.

**Causa:** El bloque `server { listen 80; }` de Nginx en VM101 tenía un redirect 301 a HTTPS.
EC2 proxeaba por HTTP (`proxy_pass http://10.8.0.2:80`), recibía el redirect y entraba
en bucle al no poder completar el HTTPS hacia VM101.

**Solución:** Eliminar el redirect en el bloque 80 de VM101. El HTTPS termina en EC2
(que sí tiene certificado Let's Encrypt). Dentro del túnel WireGuard el tráfico
va en HTTP, lo cual es seguro porque el túnel ya está cifrado.

---

### P-08 — SQL con producto cartesiano en la función de notificación

**Síntoma:** El email de notificación al vendedor llegaba multiplicado (varios emails
por cada asignación) o con datos mezclados entre reservas.

**Causa:** La consulta SQL no filtraba correctamente por el ID de reserva, generando
un producto cartesiano entre las tablas `reservas`, `clientes`, `coches` y `empleados`.

**Solución:** Reescribir la consulta usando JOINs explícitos con las condiciones `ON` correctas
y el filtro `WHERE r.id = %s` para anclar la consulta a la reserva específica.

---

## Windows Server / Active Directory

### P-09 — Los equipos no recibían IP por DHCP en algunas VLANs

**Síntoma:** Clientes en VLANs específicas no obtenían dirección IP aunque el scope DHCP existía.

**Causa:** El relay DHCP (`ip helper-address 10.0.87.10`) no estaba configurado en la SVI
de esa VLAN en los switches core. Sin relay, las broadcast DHCP no llegan al servidor.

**Solución:** Añadir `ip helper-address 10.0.87.10` en cada SVI de VLAN con DHCP dinámico
tanto en CD-1 como en CD-2.

---

### P-10 — Entra Connect: el wizard no completaba el login con Microsoft

**Síntoma:** Al ejecutar el wizard de configuración de Entra Connect, la ventana de login
de Microsoft no cargaba correctamente en Windows Server.

**Causa:** El wizard utiliza WebView2 (Edge embebido) para mostrar la página de autenticación.
La versión de Edge instalada en Windows Server era antigua y no soportaba la página de login moderna.

**Solución:** Actualizar Edge antes de ejecutar el wizard (`edge://settings/help`).
Como workaround para la presentación, los usuarios se crearon manualmente en Azure
con UPNs que coinciden con los del AD local — Entra Connect los vinculará automáticamente
cuando el wizard se complete.
