# SOC Incident Response Playbook
**Clasificación:** SENSIBLE — Solo personal de Seguridad y TI | **Versión:** 3.1 | **Revisión:** Diciembre 2025

---

## Niveles de Severidad

| Nivel | Nombre | Definición | SLA Respuesta |
|---|---|---|---|
| **P1** | Crítico | Brecha activa confirmada, ransomware en propagación, exfiltración de datos en curso | 15 min |
| **P2** | Alto | IOC de alta confianza, movimiento lateral sospechoso, cuenta privilegiada comprometida | 1 hora |
| **P3** | Medio | Anomalías de comportamiento, alertas SIEM sin confirmar, phishing exitoso (sin escalada) | 4 horas |
| **P4** | Bajo | Alertas de política, actividad inusual de bajo riesgo | 24 horas |

---

## Contactos de Emergencia (P1/P2)

| Rol | Nombre | Teléfono | Email |
|---|---|---|---|
| CISO | Carlos Mendez | +34 611 847 293 | c.mendez@acmecorp.com |
| CTO | Ana Villanueva | +34 612 033 841 | a.villanueva@acmecorp.com |
| SOC Lead | Javier Romero | +34 609 774 512 | j.romero@acmecorp.com |
| Legal / DPO | María Santos | +34 615 229 087 | dpo@acmecorp.com |
| CrowdStrike TAM | — | +1 888 512 8906 | support@crowdstrike.com |
| Cyber Insurance | Allianz Cyber | +49 89 3800 0 | claims-cyber@allianz.com |

**Canal de guerra (P1):** Slack #incident-war-room (privado, acceso por invitación del SOC Lead)

---

## Playbook: Ransomware / Cifrado masivo

### Detección
- Alerta CrowdStrike Falcon: `Ransomware.GenericEncryption` o `Process.FileEncryptor`
- Múltiples alertas de modificación masiva de ficheros en shares SMB
- Usuarios reportando que sus ficheros tienen extensión desconocida

### Contención inmediata (primeros 15 min)
1. **Aislar** el host afectado de la red (desactivar NIC desde consola Falcon o desconectar físicamente)
2. **NO apagar** el equipo — preservar memoria RAM para análisis forense
3. Identificar la cuenta que inició el proceso cifrador
4. Comprobar si la cuenta tiene acceso a otros sistemas (AD, shares de red)
5. Bloquear la cuenta en Active Directory: `Disable-ADAccount -Identity <usuario>`
6. Notificar al SOC Lead y escalar a P1 si hay más de 1 host afectado

### Erradicación
1. Identificar el vector inicial (phishing, exploit, credencial robada) mediante logs de CrowdStrike
2. Revocar tokens y sesiones activas del usuario comprometido
3. Escanear con Falcon Real Time Response todos los hosts del mismo segmento de red
4. Aplicar indicadores de compromiso (IOC) al Custom IOA de CrowdStrike

### Recuperación
1. Validar los backups en Veeam (`backup-mgmt.acmecorp.internal`)
2. Restaurar desde el último snapshot limpio (verificar integridad con hash SHA-256)
3. Monitorización intensiva 72h post-incidente

---

## Playbook: Exfiltración de Datos

### Detección
- Alerta DLP: transferencia masiva hacia IPs externas no categorizadas
- Alerta CASB: subida de datos a servicios cloud no autorizados
- Falcon: `Network.DataExfiltration` o `DNS.Tunneling`

### Contención
1. Bloquear la IP destino en el firewall perimetral (Palo Alto NGFW)
2. Revocar credenciales del usuario implicado
3. Capturar tráfico de red con NetWitness para análisis posterior
4. Evaluar qué datos fueron accedidos: consultar logs del DLP (Symantec DLP) y SIEM (Splunk)

### Notificación Legal
Si los datos exfiltrados incluyen **datos personales de clientes (PII)**, es obligatorio notificar a la AEPD en un plazo máximo de **72 horas** (RGPD Art. 33). Contactar inmediatamente con el DPO (dpo@acmecorp.com).

---

## Playbook: Compromiso de Cuenta Privilegiada

### Indicadores
- Login desde país/IP inusual con cuenta de administrador
- Escalada de privilegios fuera de horario laboral
- Modificaciones masivas en AD o GPO

### Respuesta
1. Forzar cierre de todas las sesiones activas del usuario: `Revoke-AzureADUserAllRefreshToken`
2. Resetear contraseña y revocar todos los tokens MFA
3. Revisar logs de Active Directory (últimas 48h): creación de cuentas, cambios de grupo, GPO
4. Auditar accesos a sistemas críticos desde esa cuenta (prod DB, VPN, GitHub)

---

## Herramientas del SOC

| Herramienta | URL | Credencial |
|---|---|---|
| CrowdStrike Falcon | falcon.crowdstrike.com | SSO corporativo |
| Splunk SIEM | splunk.acmecorp.internal:8000 | SSO corporativo |
| Palo Alto Panorama | panorama.acmecorp.internal | Gestión de firewall |
| Veeam Backup | backup-mgmt.acmecorp.internal | Cuenta de servicio (ver PAM) |
| CyberArk PAM | pam.acmecorp.internal | Credenciales privilegiadas bajo custodia |

---

## Post-Incidente

Dentro de las **48 horas** del cierre del incidente:
1. Redactar informe de incidente en Confluence (`wiki/SOC/Incidents/YYYY-MM`)
2. Actualizar reglas de detección en Falcon Custom IOA si se identificaron TTP nuevas
3. Revisión de lecciones aprendidas con el equipo (reunión 30 min)
4. Si P1/P2: presentar resumen ejecutivo al CISO en 5 días hábiles

*Clasificación: SENSIBLE — No distribuir fuera del equipo de Seguridad sin aprobación del SOC Lead*
