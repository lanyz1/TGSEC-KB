## Bypass Techniques

| Defense | Bypass / Recon Strategy |
|---|---|
| Branded `customlogin.aspx` with lockout / CAPTCHA / MFA | `/_vti_bin/Authentication.asmx` legacy SOAP — none of those protections apply |
| `WWW-Authenticate: NTLM` requires authenticated callers | Default IIS `extendedProtection=None` lets you elicit the Type-2 challenge anonymously — see `hunt-ntlm-info` |
| `MicrosoftSharePointTeamServices` header stripped at ELB | Body of `/_layouts/15/start.aspx` leaks version anyway; also `/_api/contextinfo`'s `LibraryVersion` |
| `/_vti_bin/lists.asmx` 403 (SharedAccess.asmx / Authentication.asmx still open) | Different services have different ACLs; enumerate all asmx separately |
| `/_api/web/CurrentUser` 401 with stack-trace JSON | Stack traces leak even on auth-deny responses; combine with version disclosure |
| Anonymous `__REQUESTDIGEST` issued (ToolShell precondition) | Pair with anonymous ToolPane POST + unencrypted ViewState; the deserialization sink yields RCE without machineKey — machineKey is then dumped by the shell for persistent re-exploitation |
| Custom error pages set | Trigger different code paths (XML-shaped ViewState → dual-parser error differential — see `hunt-aspnet`) |
| WAF blocks `<` in query | Move payload to Cookie / Referer / SOAP body — request validator doesn't reach those contexts |
| `Microsoft.SharePoint.WebPartPages.DataFormWebPart` blocked via SafeControl patch | Enumerate SafeControl list; find a subclass that bypasses the inheritance gate |
| HTTP/2 H2.CL smuggling | AWS ALBs often don't advertise `h2` ALPN — close that family early via `openssl s_client -alpn h2,http/1.1` |
| Authenticate.aspx wraps `Source=` in ReturnUrl | Test post-auth behavior with valid creds; pre-auth chain wraps everything safely |

---

