# Sample Data — Ransomware Scenario

This directory contains synthetic incident response data for demonstrating the
IR Dashboard. **All data is completely fictional.** No real names, companies, IP
addresses, or PII appear in these files.

## Scenario

**Nexora Technologies** — a fictional mid-size technology company — suffered a
ransomware attack over the period of July 14–19, 2026.

### Attack Timeline

| Date | Phase | Key Events |
|------|-------|------------|
| Jul 14 | Initial access | Phishing email delivered to VP Engineering. Credentials harvested. First attacker login from NL proxy. |
| Jul 15 | Reconnaissance | Attacker browses SharePoint and Azure Portal. Failed credential stuffing against IT admin. RDP access established. |
| Jul 16 | Lateral movement | Compromised service account (svc-backup) used for RDP to file server. Database credentials exfiltrated. |
| Jul 17 | Persistence | Continued RDP sessions via service account. Backup server accessed. |
| Jul 18 | Exfiltration | Data staged and uploaded to external endpoint (SG) via azcopy. Cleanup of staged archives. |
| Jul 19 | Ransomware | PsExec used to deploy ransomware across DC, file server, DB servers. Ransom note dropped. Extortion emails sent. |

### Fictional Entities

- **Company**: Nexora Technologies (nexora.com)
- **Compromised user**: sarah.chen@nexora.com (VP Engineering)
- **Service account abused**: svc-backup@nexora.com
- **Attacker IPs**: 192.0.2.47, 198.51.100.12, 203.0.113.88 (RFC 5737 documentation ranges)
- **Internal IPs**: 10.10.5.x (workstations), 10.10.3.x (servers)

### Data Files

| File | Records | Mimics | Description |
|------|---------|--------|-------------|
| `signin_events.json` | 33 | AADSignInEventsBeta | Cloud sign-in events with attacker IPs, error codes, and geo data |
| `file_operations.json` | 24 | CloudAppEvents | SharePoint/OneDrive file downloads, uploads, and ransomware note drops |
| `email_events.json` | 15 | EmailEvents | Phishing delivery, exfil emails to external drops, and extortion messages |
| `identity_logon_events.json` | 24 | IdentityLogonEvents | On-prem authentication showing RDP lateral movement and PsExec deployment |

## Usage

1. Copy these files into your project's `incoming/` directory
2. Run the intake process (via dashboard or `python scripts/intake.py`)
3. The dashboard will auto-detect the JSON files and display them in the Atomic Events viewer
4. Use the global search to hunt across all data sources simultaneously
