# Guía de Onboarding — AcmeCorp Financial Services
**Clasificación:** PÚBLICO | **Versión:** 4.2 | **Última revisión:** Enero 2026

---

## Bienvenido a AcmeCorp

AcmeCorp Financial Services es una firma multinacional de servicios financieros con sede en Madrid, con oficinas en Londres, Frankfurt, Nueva York y Singapur. Gestionamos más de 48.000 millones de euros en activos bajo administración y damos servicio a más de 3 millones de clientes en 19 países.

---

## 1. Herramientas Corporativas

| Herramienta | URL / Acceso | Uso |
|---|---|---|
| **Slack** | acmecorp.slack.com | Comunicación interna |
| **Jira** | jira.acmecorp.internal | Gestión de proyectos |
| **Confluence** | wiki.acmecorp.internal | Documentación técnica |
| **GitHub Enterprise** | github.acmecorp.internal | Repositorios de código |
| **Workday** | acmecorp.workday.com | RRHH, nóminas, vacaciones |
| **ServiceDesk** | helpdesk.acmecorp.internal | Soporte IT |
| **CorpAI Assistant** | ai.acmecorp.internal | Asistente IA corporativo |

---

## 2. Solicitud de Accesos

Todos los accesos se gestionan mediante tickets en ServiceDesk (1–3 días laborables).

1. Abre un ticket en `helpdesk.acmecorp.internal` → categoría "Access Request"
2. Indica sistema, nivel de acceso requerido y justificación de negocio
3. Obtén aprobación de tu responsable directo

**Sistemas de nivel restringido** (requieren aprobación adicional del CISO):
- Entornos de producción (prod-*)
- Sistemas de datos de clientes (PII/PCI)
- Herramientas de seguridad (SIEM, EDR)

---

## 3. Política de Seguridad

- **MFA obligatorio** en todos los sistemas sin excepción (Microsoft Authenticator o YubiKey)
- Contraseñas: mínimo 16 caracteres, rotación cada 90 días
- Solo dispositivos **gestionados por IT** (MDM activo) pueden acceder a sistemas internos
- Documentos SENSIBLE/SECRETO: prohibido almacenarlos en Google Drive, Dropbox u otros servicios cloud públicos
- **No compartir credenciales** por ningún canal

---

## 4. Red y VPN

Para acceso remoto a recursos internos:
- Cliente VPN: **GlobalProtect** (descarga desde portal IT)
- Servidor: `vpn.acmecorp.com` (SSO corporativo + MFA)
- Split tunneling **desactivado** en modo teletrabajo

WiFi de oficina:
- `ACME-CORP` — red corporativa (requiere certificado de dispositivo)
- `ACME-GUEST` — solo internet, para visitas

---

## 5. Contactos Útiles

| Rol | Contacto |
|---|---|
| IT Helpdesk | helpdesk@acmecorp.com · Slack #it-support |
| SOC (incidentes) | soc@acmecorp.com · Slack #security-alerts |
| RRHH | people@acmecorp.com |

---

## 6. Primeros 30 días

- **Semana 1:** Configuración de herramientas y accesos básicos
- **Semana 2–3:** Formación obligatoria de seguridad en Learn@AcmeCorp *(plazo: 15 días hábiles)*
- **Mes 1:** Reunión de seguimiento con mánager y HR Business Partner

*Dudas: people@acmecorp.com*
