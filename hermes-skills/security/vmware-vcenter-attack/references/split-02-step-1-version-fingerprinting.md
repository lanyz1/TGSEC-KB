## Step 1 — Version fingerprinting

```bash
TARGET="vcenter.target.com"

# Build info endpoint (often public; revealing exact patch level)
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/sdk/vimServiceVersions.xml"

# UI build (visible in page source)
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/ui/login" | grep -oE 'build[^"]{0,40}'
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/ui/" | grep -oE 'vsphere[^"]{0,40}'

# REST API version (vSphere 7+)
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/api/appliance/system/version"

# Cert metadata
echo | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alt"

# SSO Admin Service (info disclosure)
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/sso-adminserver/sdk/vsphere.local"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/websso/SAML2/Metadata/vsphere.local"
```

Map build → version → CVE applicability via VMware advisories (vmware.com/security/advisories).

---

