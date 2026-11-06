## Crown Jewel Targets

SharePoint Server (on-prem) is one of the richest enterprise attack surfaces in 2025-2026 bug bounty / red-team work. Three forces converge:

1. **End-of-life unpatched code paths.** SharePoint Server 2013 reached extended-support EoL on 2023-04-11 (final build `15.0.5545.1000` / KB5002381). Every SharePoint CVE published after that date is **permanently unpatched** on SP2013 farms. SP2016 reaches EoL 2026-07-14; SP2019 reaches EoL 2026-07-14 (next 2 months as of May 2026); only SP Subscription Edition is currently in active support.
2. **CVE-2025-53770 / 53771 "ToolShell"** — July 2025 emergency-out-of-band patch chain for SPE / SP2019 / SP2016. The vulnerable code path (anonymous `/_layouts/15/ToolPane.aspx?DisplayMode=Edit` + anonymous `__REQUESTDIGEST` + unencrypted ViewState) is present in **SP2013 too** and will never receive a fix.
3. **Custom branded login pages forget legacy SOAP login.** `/_vti_bin/Authentication.asmx` with the `Login` SOAP op is the SharePoint equivalent of WordPress XMLRPC bypass — accepts native Forms credentials anonymously with no rate limit on most farms even when the branded UI has lockout.

**Highest-value SharePoint targets:**

- **SP2013 farms still on the public internet** — every CVE since April 2023 is unpatched. Critical-severity findings.
- **Dealer / partner / supplier portals** built on SharePoint by enterprise integrators (German VW group, a enterprise system integrator, etc.) — high-impact business data, often nested inside corporate AD trees.
- **SharePoint farms with anonymous Forms-auth zones** — Authentication.asmx becomes anonymously brute-forceable.
- **SharePoint inside corporate AD parent forests** — NTLM Type-2 leak (see `hunt-ntlm-info`) discloses the parent forest membership.
- **Telerik-integrated SharePoint installations** — additional deserialization sinks on top of SP's own.

**Asset types that pay most:** internet-reachable SP Server (any version) > SP Online with custom solutions hooks > intranet SP only after VPN compromise.

---

