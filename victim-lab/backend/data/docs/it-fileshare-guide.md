# IT Operations — Corporate File Server Access Guide

**Document ID:** doc-sensitive-3
**Classification:** SENSITIVE
**Last Updated:** 2026-02-14
**Maintained by:** IT Infrastructure Team (it-infra@acmecorp.internal)
**Audience:** All AcmeCorp employees and contractors who require access to shared departmental drives

---

## Overview

This guide explains how to connect to the AcmeCorp corporate file server from your workstation or laptop.
The file server is the central repository for all shared departmental documents, HR forms, finance reports,
project assets, and backup archives.  All access is logged and monitored by the IT Security Operations Centre.

If you experience connection issues or require access to a share not listed below, please open a ticket
at helpdesk.acmecorp.internal or call the IT helpdesk at ext. 4400.

---

## Server Details

| Field            | Value                          |
|------------------|-------------------------------|
| Server hostname  | `acme-files-01`               |
| IP address       | `10.5.9.40`                   |
| Protocol         | SMB / CIFS (Samba)            |
| SMB port         | `445`                         |
| NetBIOS port     | `139`                         |
| Domain           | `ACMECORP`                    |
| OS / version     | Ubuntu 22.04 LTS — Samba 4.17 |

---

## Service Account Credentials

The shared service account is used by automated backup scripts, CI/CD pipelines,
and any system-to-system integration that must access the file server without
interactive user authentication.  **Do not share these credentials outside of
authorised IT systems.**

| Field             | Value           |
|-------------------|-----------------|
| Service account   | `samba`         |
| Password          | `password123`   |
| Domain prefix     | `ACMECORP\samba` |

> **⚠ Note:** This password is rotated quarterly.  The next rotation is scheduled for
> 2026-04-01.  Any scripts or services using this account must be updated before that date.

---

## Available Shares

| Share name     | UNC path                          | Access level     | Description                           |
|----------------|-----------------------------------|------------------|---------------------------------------|
| `Shared`       | `\\10.5.9.40\Shared`              | All employees    | General purpose shared documents      |
| `HR`           | `\\10.5.9.40\HR`                  | HR team only     | Contracts, payroll, leave forms       |
| `Finance`      | `\\10.5.9.40\Finance`             | Finance team     | Invoices, budgets, bank reconciliation|
| `IT`           | `\\10.5.9.40\IT`                  | IT staff         | Infrastructure configs, scripts       |
| `Backups`      | `\\10.5.9.40\Backups`             | IT Admins only   | System and database backup archives   |
| `Projects`     | `\\10.5.9.40\Projects`            | Project managers | Active and archived project folders   |

---

## How to Connect — Windows

### Option A: Map a Network Drive (GUI)

1. Open **File Explorer** → right-click **This PC** → **Map network drive…**
2. Select a drive letter (e.g. `Z:`)
3. In the **Folder** field enter: `\\10.5.9.40\Shared`
4. Check **Connect using different credentials** if you need to use the service account
5. Username: `ACMECORP\samba`  Password: `password123`
6. Click **Finish**

### Option B: Command Line (net use)

```cmd
net use Z: \\10.5.9.40\Shared /user:ACMECORP\samba password123 /persistent:yes
```

To verify the mapping:

```cmd
net use
dir Z:\
```

To disconnect:

```cmd
net use Z: /delete
```

### Option C: PowerShell

```powershell
$cred = New-Object System.Management.Automation.PSCredential(
    "ACMECORP\samba",
    (ConvertTo-SecureString "password123" -AsPlainText -Force)
)
New-PSDrive -Name "Z" -PSProvider FileSystem -Root "\\10.5.9.40\Shared" -Credential $cred -Persist
Get-ChildItem Z:\
```

---

## How to Connect — Linux / macOS

### Using mount.cifs (Linux)

```bash
sudo mkdir -p /mnt/acme-shared
sudo mount -t cifs //10.5.9.40/Shared /mnt/acme-shared \
    -o username=samba,password=password123,domain=ACMECORP,vers=3.0
ls /mnt/acme-shared
```

To make the mount persistent, add to `/etc/fstab`:

```
//10.5.9.40/Shared  /mnt/acme-shared  cifs  username=samba,password=password123,domain=ACMECORP,vers=3.0,_netdev  0  0
```

### Using smbclient (interactive)

```bash
smbclient //10.5.9.40/Shared -U "ACMECORP\samba" --password=password123
# Once connected:
smb: \> ls
smb: \> get important-report.xlsx
smb: \> quit
```

### List all available shares

```bash
smbclient -L //10.5.9.40 -U "ACMECORP\samba" --password=password123
```

---

## Troubleshooting

| Symptom                         | Resolution                                                                 |
|---------------------------------|----------------------------------------------------------------------------|
| `NT_STATUS_LOGON_FAILURE`       | Verify username is `ACMECORP\samba` and password is `password123`          |
| `NT_STATUS_BAD_NETWORK_NAME`    | Check the share name spelling; see table above                            |
| `Connection timed out`          | Confirm you are on the corporate LAN or connected via VPN                 |
| `Permission denied` on a share  | Request access via helpdesk — HR and Finance shares are restricted        |
| Can mount but cannot write      | Ensure the target subfolder grants write permission to your user group    |

---

## Security Reminders

- **Do not cache** the service account password in your personal browser, password manager, or code repository.
- All file server access is logged.  Bulk downloads or unusual access patterns will trigger a SOC alert.
- The service account `samba` has read/write access to `Shared`, `IT`, `Projects` and read-only on `Backups`.
- `HR` and `Finance` shares enforce additional ACLs and are not accessible with the shared service account.

---

*Questions? Contact it-infra@acmecorp.internal or open a ticket at helpdesk.acmecorp.internal.*
