## Step 6 — SSO / vmdir LDAP enumeration

```bash
# SSO Admin endpoint (frequently exposes domain info)
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/websso/SAML2/Metadata/vsphere.local" | xmllint --format -

# Extract Identity Source info
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/sso-adminserver/sdk/vsphere.local"

# Try anonymous LDAP bind to vmdir (port 389/636 if exposed)
ldapsearch -x -H "ldap://$TARGET:389" -b "" -s base
ldapsearch -x -H "ldap://$TARGET:389" -b "cn=Configuration,cn=vmware,cn=cis,dc=vsphere,dc=local"
```

---

