# Punto de expansión — Autenticación Azure AD en el portal de empleados

> **Estado:** No implementado. Identificado como punto de expansión natural del proyecto.
> **Motivo:** Fuera del alcance del Sprint 3 por restricciones de tiempo.

---

## Qué representa la línea EC2 ↔ Azure en el diagrama

En el diagrama de topología aparece una conexión entre **AWS EC2** y **Microsoft Azure / Entra ID**.
Esta conexión no está activa en la implementación actual, pero representa una integración
planificada y arquitectónicamente coherente con el resto de la infraestructura.

## El problema que resolvería

El portal de empleados (`/admin`) actualmente autentica con email + contraseña almacenada
en MariaDB local. Esto implica gestionar credenciales separadas para la web, independientes
de las cuentas corporativas que ya tienen los empleados en Active Directory y Azure AD.

## La solución planteada

Integrar **Azure AD (Entra ID) como proveedor de identidad** para el login de empleados
mediante el protocolo **OAuth2 / OpenID Connect**.

El flujo sería:
```
Empleado → exoticmotors.duckdns.org (EC2)
    → Flask redirige a login.microsoftonline.com
    → Empleado se autentica con su cuenta corporativa @exoticmotors
    → Azure redirige al callback de Flask (vía EC2)
    → Flask valida el token → acceso a /admin
```

## Por qué encaja con la infraestructura existente

- Los empleados ya tienen cuentas en Azure AD gracias a **Entra Connect** (sincronizado desde el AD local en VM102)
- El certificado HTTPS de EC2 (Let's Encrypt) ya cubre el redirect URI
- No requiere cambios en la red ni en el firewall
- Permite habilitar MFA corporativo sin modificar la web

## Impacto en la arquitectura

Con esta integración implementada, la línea EC2 ↔ Azure pasaría a representar
el flujo OAuth2 de autenticación: la aplicación web pública llama a los endpoints
de Azure AD para validar las identidades corporativas de los empleados.

La documentación técnica paso a paso de esta integración está disponible
en el repositorio privado del proyecto.
