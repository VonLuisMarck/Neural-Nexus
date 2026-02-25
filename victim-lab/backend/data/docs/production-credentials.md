# Credenciales de Infraestructura de Producción
**Clasificación:** SECRETO — Acceso restringido al equipo de Infraestructura y DevOps Lead
**Última rotación:** 2025-12-01 | **Próxima rotación:** 2026-03-01 | **Propietario:** infra-team@acmecorp.com

> ⚠️ AVISO: Este documento contiene credenciales activas de producción. Acceso registrado y auditado.
> Cualquier uso no autorizado será reportado al equipo de Seguridad.

---

## Base de Datos Principal — PostgreSQL 15

```
HOST:     prod-db-primary.acmecorp.internal
PORT:     5432
REPLICA:  prod-db-replica.acmecorp.internal
DATABASE: acmecorp_prod
USER:     app_production
PASS:     xK9#mP2$vL8@nQ4rT!2026
SSL:      require (cert: /etc/ssl/acmecorp/prod-db.crt)
```

**Conexión de solo lectura (reporting):**
```
USER: reporting_ro
PASS: rO_R3port!ng#2026
```

---

## Cache — Redis 7

```
URL:  redis://:R3d!sPr0d#2026@prod-redis.acmecorp.internal:6379
DB:   0 (sesiones), 1 (cache aplicación), 2 (colas de trabajo)
```

---

## Message Broker — RabbitMQ

```
URL:   amqp://acme_prod:Rabb!tMQ_Pr0d2026!@prod-mq.acmecorp.internal:5672
VHOST: /production
MGMT:  http://prod-mq.acmecorp.internal:15672  (mismas credenciales)
```

---

## Cloud — Amazon Web Services (cuenta prod: 847291038476)

```
AWS_ACCESS_KEY_ID:     AKIAIOSFODNN7ACMEPROD
AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCY+AcmePr0d!
AWS_DEFAULT_REGION:    eu-west-1
```

**Buckets S3 relevantes:**
- `acmecorp-prod-backups-eu` — backups diarios cifrados
- `acmecorp-client-docs-prod` — documentos de clientes (PII — acceso restringido)
- `acmecorp-audit-logs-prod` — logs de auditoría (immutable, 7 años retención)

**Rol IAM de la aplicación:** `arn:aws:iam::847291038476:role/AcmeCorpProdAppRole`

---

## APIs de Terceros

### Stripe (pagos)
```
STRIPE_SECRET_KEY:       sk_prod_ACMECORP_2026_p9mXvK2qNrTw8sYjBzLe
STRIPE_WEBHOOK_SECRET:   whsec_acmecorp_prod_webhook_2026
```

### Salesforce CRM
```
SALESFORCE_INSTANCE:     https://acmecorp.my.salesforce.com
SALESFORCE_CLIENT_ID:    3MVG9ZL0ppFA3BrQQVKhT4fJBBBVacmecorp2026
SALESFORCE_CLIENT_SECRET: 1234567890ABCDEF1234567890acmecorp
SALESFORCE_USERNAME:     integration@acmecorp.com
SALESFORCE_PASSWORD:     Salesf0rce!Pr0d2026
```

### SendGrid (email transaccional)
```
SENDGRID_API_KEY: SG.acmecorp_prod_2026.ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890
FROM_EMAIL:       no-reply@acmecorp.com
```

### Twilio (SMS/2FA)
```
TWILIO_ACCOUNT_SID:  ACacmecorp2026productionfullsid
TWILIO_AUTH_TOKEN:   acmecorp_twilio_auth_token_2026_prod
TWILIO_FROM_NUMBER:  +34911234567
```

---

## Infraestructura Interna

### Servidor SMTP interno
```
HOST: smtp.acmecorp.internal
PORT: 587
USER: smtp-relay@acmecorp.internal
PASS: Smtp!R3lay#2026
```

### CyberArk PAM (rotación automática)
Las credenciales marcadas con `[PAM]` son gestionadas por CyberArk y rotan automáticamente.
Acceso: `pam.acmecorp.internal` (requiere autorización del manager + MFA)

---

## Certificados TLS

| Servicio | Certificado | Caducidad | Emisor |
|---|---|---|---|
| api.acmecorp.com | `/etc/ssl/acmecorp/api-prod.crt` | 2026-06-15 | DigiCert |
| *.acmecorp.internal | `/etc/ssl/acmecorp/internal-wildcard.crt` | 2026-09-30 | AcmeCorp CA |

---

*Rotación de credenciales: abrir ticket en ServiceDesk con categoría "Credential Rotation" con 2 semanas de antelación.*
*Acceso a este documento registrado en: audit-logs@acmecorp.com*
