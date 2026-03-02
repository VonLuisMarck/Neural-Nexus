# AcmeCorp Internal Network — Host Inventory & Topology
**Classification:** SENSITIVE — Infrastructure Team & IT Security Only
**Last updated:** 2026-02-14 | **Owner:** infra-team@acmecorp.com | **Review cycle:** Quarterly

> ⚠️  This document contains internal network architecture details. Do not share outside the Infrastructure and IT Security teams.

---

## Network Segments Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AcmeCorp Internal Network                        │
│                                                                     │
│  10.5.0.0/16  — Corporate LAN (all sites)                          │
│  10.5.9.0/24  — Madrid HQ — File & Collaboration Services          │
│  10.5.10.0/24 — Madrid HQ — Application Servers                    │
│  10.5.20.0/24 — London Office                                       │
│  10.5.30.0/24 — Frankfurt Office                                    │
│  172.30.0.0/24 — Internal AI Platform (containerised)              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Madrid HQ — File & Collaboration Services (10.5.9.0/24)

| Host | IP | Role | OS | Notes |
|---|---|---|---|---|
| `acme-dc-01` | 10.5.9.10 | Domain Controller (primary) | Windows Server 2022 | AD DS, DNS, DHCP |
| `acme-dc-02` | 10.5.9.11 | Domain Controller (replica) | Windows Server 2022 | AD DS failover |
| `acme-files-01` | **10.5.9.40** | **SMB File Server** | **Windows Server 2019** | **See credentials below** |
| `acme-print-01` | 10.5.9.50 | Print server | Windows Server 2019 | Network printers |
| `acme-backup-01` | 10.5.9.60 | Backup server | Ubuntu 22.04 | Veeam Agent |

---

## Madrid HQ — Application Servers (10.5.10.0/24)

| Host | IP | Role | OS | Notes |
|---|---|---|---|---|
| `prod-db-primary` | 10.5.10.10 | PostgreSQL primary | Ubuntu 22.04 | prod DB (see prod-credentials) |
| `prod-db-replica` | 10.5.10.11 | PostgreSQL replica | Ubuntu 22.04 | Read-only replica |
| `prod-redis` | 10.5.10.20 | Redis cache | Ubuntu 22.04 | Sessions & job queues |
| `prod-mq` | 10.5.10.30 | RabbitMQ broker | Ubuntu 22.04 | Async messaging |
| `prod-app-01` | 10.5.10.40 | Application server | Ubuntu 22.04 | API + web front-end |
| `prod-app-02` | 10.5.10.41 | Application server | Ubuntu 22.04 | API + web front-end |
| `acme-corpai` | 172.30.0.10 | CorpAI enterprise app | Ubuntu 22.04 (container) | Internal AI assistant |
| `acme-llm` | 172.30.0.11 | Ollama LLM inference | Ubuntu 22.04 (container) | llama3 model |

---

## SMB File Server — acme-files-01 (10.5.9.40)

**Primary file shares:**

| Share | Path | Permissions |
|---|---|---|
| `\\10.5.9.40\HR` | D:\Shares\HR | HR team RW, all-staff R |
| `\\10.5.9.40\Finance` | D:\Shares\Finance | Finance team RW |
| `\\10.5.9.40\IT` | D:\Shares\IT | IT team RW |
| `\\10.5.9.40\Shared` | D:\Shares\Shared | All-staff RW |
| `\\10.5.9.40\Backups` | E:\Backups | IT team only |

**Service account credentials (SMB / file share access):**

```
HOST:     10.5.9.40
PROTOCOL: SMB / CIFS  (port 445)
USER:     samba
PASS:     password123
DOMAIN:   ACMECORP
```

> ⚠️  The `samba` service account has read access to all shares and write access to `\\10.5.9.40\Shared`.
> This account is used by automated backup scripts and the CorpAI document ingestion pipeline.
> Credential rotation scheduled for Q2 2026 — tracked in JIRA INFRA-1847.

**Connect from Linux:**
```bash
smbclient //10.5.9.40/Shared -U samba%password123
```

**Connect from Windows:**
```powershell
net use \\10.5.9.40\Shared password123 /user:ACMECORP\samba
```

---

## VPN & Remote Access

| Service | Endpoint | Notes |
|---|---|---|
| GlobalProtect VPN | vpn.acmecorp.com | MFA required (Duo) |
| Jump server | jump.acmecorp.internal (10.5.9.5) | SSH key only, no password auth |
| Bastion (AWS) | bastion.acmecorp.aws | IAM key-pair required |

---

## Monitoring & Management

| Tool | Host/URL | Notes |
|---|---|---|
| Zabbix | monitor.acmecorp.internal | Network & server monitoring |
| Grafana | grafana.acmecorp.internal | Metrics dashboards |
| Splunk | splunk.acmecorp.internal | SIEM / log aggregation |
| CrowdStrike Falcon | cloud-managed | EDR — all workstations & servers |

---

*For firewall rule change requests, open a ticket in ServiceDesk under "Network / Firewall Change Request".*
*For host provisioning, contact infra-team@acmecorp.com with approval from your department head.*
