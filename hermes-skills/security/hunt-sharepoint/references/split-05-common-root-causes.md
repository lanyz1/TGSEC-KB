## Common Root Causes

1. **`/_vti_bin/Authentication.asmx` left enabled on the public-zone IIS binding.** SharePoint admins enable Forms auth on a custom login UI and don't realise the legacy SOAP Login endpoint is independently reachable.

2. **`viewStateEncryption="Auto"` on layouts pages.** SharePoint's default ViewState mode signs-only for pages without sensitive form fields. Pages like ToolPane.aspx have `__VIEWSTATEENCRYPTED=""` — exploitable if machineKey leaks.

3. **`/_api/contextinfo` POST accessible anonymously.** SharePoint Online and SPE 2024-07+ require auth on contextinfo. Earlier versions and most SP2013 farms allow anonymous POST → FormDigest token returned with 1800s validity. This is the second ToolShell precondition.

4. **NTLM enabled on public-zone IIS binding.** Default dual-auth (Forms + NTLM) leaves NTLM Negotiate available to anonymous internet users. Type-2 challenge leaks AD topology.

5. **SP2013 farms past EoL still internet-exposed.** Microsoft extended support ended 2023-04-11. Every post-April-2023 SharePoint CVE is unpatched. Common in enterprise integrator scenarios (system-integrator inside corporate-parent AD, SI-managed dealer portals).

6. **`<SafeControl>` whitelist in web.config trusted as the only gate.** Picker.aspx enforces an `instanceof PickerDialog` check, which is patched against the original CVE-2019-0604 vector — but the underlying SafeControl model itself is anonymously enumerable via the Picker.aspx error differential.

7. **AWS ELB + SP IIS without explicit Transfer-Encoding normalization.** Default ELB forwards `Transfer-Encoding` to back-end IIS; IIS interprets `Content-Length` when both are present in a way that desyncs from ELB. Multiple TE-obfuscation variants bypass simple WAF rules.

8. **Default Windows-installer hostname (`WIN-XXXXXXXXXXX`) never renamed.** Signal of rushed provisioning; correlates with default service-account passwords on SQL backend, default farm-account passwords on Central Admin, etc.

9. **Custom-branding module (`/_layouts/15/<Customer>/`) JS bundles loaded with `?v=YYYYMMDD` query strings.** The query string reveals last-modified date — useful for "this app is actively maintained" vs "this app is abandoned" determination.

10. **Cross-node ViewState MAC failures when AWS ELB doesn't pin session affinity to one WFE.** Operationally broken (users hit 500s on every POST); security-wise broadcasts farm topology in error messages.

---

