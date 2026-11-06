## Real Impact Examples

### Scenario A — a authorized SharePoint engagement against an EoL on-prem farm

Target: `https://target-portal.example/` — SharePoint Server 2013 build `15.0.5545.1000` (KB5002381 / final EoL April 2023 CU). Tenant = a system-integrator tenant (Swiss <ParentCorp> importer) inside a corporate global AD (`customer.parent-corp.example`). Server hostname `WIN-XXXXXXXXXXX` (default Windows installer pattern).

11 findings shipped: 3 Critical, 2 Medium, 6 Low/Info. The three Criticals:

1. **Authentication.asmx anonymous credential brute-force** — 10-burst test showed uniform 0.6-0.9 s timing with no rate limit, no lockout, no CAPTCHA, no MFA challenge. Identical 431-byte responses.
2. **HTTP request smuggling TE.CL** — 5/5 trials showed 12.18 s back-end hang vs 0.16 s baseline. 4 additional obfuscation variants (space-before-colon, trailing-space, lowercase, mixed-case) showed 6.16 s hang — each bypassing simple WAF rules.
3. **ToolShell precondition chain** — anonymous GET ToolPane.aspx (200) + anonymous POST `/_api/contextinfo` (200, valid FormDigest) + anonymous POST ToolPane.aspx with digest (200, no auth challenge) + `__VIEWSTATEENCRYPTED=""`. Permanent zero-day on EoL SP2013.

Plus Medium-tier: NTLM Type-2 disclosure of full AD topology (`customer.parent-corp.example`, `WIN-XXXXXXXXXXX`); SP2013 EoL exposure.

### Scenario B — `/_layouts/15/download.aspx?SourceUrl=` recognized correctly as NOT-SSRF (saved-time example)

Same target. Initial scan flagged `download.aspx?SourceUrl=http://oob.example.com/` as SSRF because the server echoed the URL in the 500 error title (`"The Web application at http://oob.example.com/ could not be found"`). 38 Collaborator-tagged payloads across 12+ URL-accepting SP parameters → zero DNS/HTTP callbacks. Conclusion: `download.aspx` is an SP-internal `SPWebApplication` / `SPFile` resolver, NOT a generic URL fetcher. The "echo" is server-side error-string formatting. Saved from reporting an N/A finding by following the `hunt-ssrf` OOB-Or-It-Didn't-Happen Gate.

### Scenario C — CVE-2019-0604 patch verification via Picker.aspx

Same target. Feeding `Microsoft.SharePoint.WebPartPages.DataFormWebPart` (the canonical CVE-2019-0604 deserialization gadget) to Picker.aspx returned `"Only PickerDialog types can be used with the dialog. The type should be configured as a safecontrol in this site."` — meaning the type EXISTS and is reachable through reflection, but the dialog framework's `instanceof PickerDialog` patch correctly rejects it. The patch IS in place for the original CVE-2019-0604 vector. The class-existence enumeration itself becomes recon for any future CVE-2019-0604-family chain that doesn't go through the inheritance gate.

---

