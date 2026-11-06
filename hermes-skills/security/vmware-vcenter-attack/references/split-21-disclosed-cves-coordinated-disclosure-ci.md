## Disclosed CVEs & coordinated-disclosure citations

These are the load-bearing public references for every CVE called out in the matrix above. Every entry includes the vendor advisory, the originating researcher writeup or KEV-catalog entry, and (where public) in-the-wild exploitation references.

### 1. CVE-2021-21972 — vCenter `vropspluginui` unauthenticated arbitrary file upload (canonical pre-auth RCE)
- **Affected:** vCenter Server 6.5 < 6.5 U3n, 6.7 < 6.7 U3l, 7.0 < 7.0 U1c (vRealize Operations vCenter plugin bundled with every default install — Linux or Windows variant matters for payload). VMware Cloud Foundation 3.x/4.x also bundles.
- **Attack flow:** Unauth POST to `/ui/vropspluginui/rest/services/uploadova` with a tar/OVA containing a path-traversal entry. On Windows write `webshell.jsp` under the vsphere-ui webroot for SYSTEM; on Linux drop `authorized_keys` under `/home/vsphere-ui/.ssh/` and SSH in.
- **Root cause:** Endpoint exposed by the vRealize Operations plugin lacked any authentication filter; the `uploadova` handler did not sanitize archive entry paths.
- **Disclosure:** Reported by Mikhail Klyuchnikov (Positive Technologies / PT SWARM) in autumn 2020; advisory + patch published 2021-02-23 as VMSA-2021-0002; PoC on GitHub the next day triggered mass scanning. **CISA KEV:** added 2021-11-03. Year discovered 2020, patched 2021.
- **References:** https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/23599 ; https://swarm.ptsecurity.com/unauth-rce-vmware/ ; https://www.tenable.com/blog/cve-2021-21972-vmware-vcenter-server-remote-code-execution-vulnerability ; https://attackerkb.com/topics/lrfxAJ9nhV/vmware-vsphere-client-unauth-remote-code-execution-vulnerability-cve-2021-21972

### 2. CVE-2021-21985 — vCenter vSAN Health Check plug-in pre-auth RCE
- **Affected:** vCenter Server 6.5 < 6.5 U3p, 6.7 < 6.7 U3n, 7.0 < 7.0 U2b (vSAN Health Check plugin is enabled by default whether or not vSAN is in use).
- **Attack flow:** Unauthenticated abuse of `ProxygenController` in the vSAN Health plugin → Java unsafe reflection chained with an SSRF primitive → arbitrary method invocation as `vsphere-ui` → command execution.
- **Root cause:** Missing input validation + dangerous reflection sink reachable from an unauthenticated REST surface.
- **Disclosure:** Reported by Ricter Z (Yang Hao) of 360 Noah Lab; advisory VMSA-2021-0010 published 2021-05-25. Public PoC and Metasploit module followed within days; honeypots saw active exploitation. Year discovered 2021, patched 2021.
- **References:** https://www.vmware.com/security/advisories/VMSA-2021-0010.html ; https://noahblog.360.cn/vcenter-server-rce/ (Ricter Z writeup) ; https://www.rapid7.com/db/modules/exploit/linux/http/vmware_vcenter_vsan_health_rce/ ; https://www.bleepingcomputer.com/news/security/vmware-warns-of-critical-bug-affecting-all-vcenter-server-installs/

### 3. CVE-2021-22005 — vCenter Analytics service arbitrary file upload → RCE
- **Affected:** vCenter Server 6.7 < 6.7 U3o, 7.0 < 7.0 U2d. Cloud Foundation 3.x/4.x bundled vCenter.
- **Attack flow:** Unauth POST to the Analytics endpoint on port 443 (`/analytics/telemetry/ph/api/hyper/send`) writes attacker-controlled file outside the intended directory; chained with subsequent service abuse to reach RCE as the vCenter service account.
- **Root cause:** Analytics/CEIP endpoint did not authenticate file uploads and did not validate target path.
- **Disclosure:** VMware advisory VMSA-2021-0020 published 2021-09-21. Working PoC by @testanull / @wvu released within ~72h; CISA issued an emergency alert 2021-09-24. **CISA KEV:** added 2021-11-03. Year discovered 2021, patched 2021.
- **References:** https://www.vmware.com/security/advisories/VMSA-2021-0020.html ; https://www.cisa.gov/news-events/alerts/2021/09/24/vmware-vcenter-server-vulnerability-cve-2021-22005-under-active-exploit ; https://www.rapid7.com/blog/post/2021/09/21/critical-vcenter-server-file-upload-vulnerability-cve-2021-22005/ ; https://www.bleepingcomputer.com/news/security/working-exploit-released-for-vmware-vcenter-cve-2021-22005-bug/

### 4. CVE-2022-22954 — Workspace ONE Access / Identity Manager FreeMarker SSTI → RCE
- **Affected:** Workspace ONE Access [REDACTED_IP], [REDACTED_IP], [REDACTED_IP], [REDACTED_IP]; Identity Manager 3.3.3 → 3.3.6; vRealize Automation 7.6.
- **Attack flow:** Unauth GET to `/catalog-portal/ui/oauth/verify?deviceUdid=${...}` injects a FreeMarker template; `freemarker.template.utility.Execute` runs OS commands as the `horizon` service account. Single-request RCE.
- **Root cause:** Catalog-portal endpoint passed attacker-controlled query parameter into FreeMarker render without sandboxing the Execute utility.
- **Disclosure:** Reported by Steven Seeley (mr_me) of Source Incite; VMware advisory VMSA-2022-0011 published 2022-04-06. PoCs public within 48h; widespread mass-exploitation followed. **CISA KEV:** added 2022-04-14. CISA AA22-138B (May 2022) documents IR engagements at "large organizations" exploited via this CVE. Year discovered 2022, patched 2022.
- **References:** https://www.vmware.com/security/advisories/VMSA-2022-0011.html ; https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-138b ; https://srcincite.io/blog/2022/04/19/cve-2022-22954-vmware-workspace-one-access-pre-auth-rce.html ; https://www.crowdsec.net/blog/new-surge-in-vmware-cve-2022-22954-exploit-attempts

### 5. CVE-2022-22972 — Workspace ONE Access / Identity Manager / vRealize Automation Host-header authentication bypass
- **Affected:** Workspace ONE Access [REDACTED_IP]; Identity Manager 3.3.3–3.3.6; vRealize Automation 7.6 (and downstream Cloud Foundation bundles).
- **Attack flow:** Manipulate the HTTP `Host` header during local-domain login flow; the server routes its internal validation request to the attacker-controlled hostname → returns admin session without legitimate credentials.
- **Root cause:** Host header used unvalidated as the target for the internal auth-validation request — classic SSRF-into-self with trust elevation.
- **Disclosure:** Reported by Bruno López of Innotec Security; VMware advisory VMSA-2022-0014 published 2022-05-18. **CISA Emergency Directive 22-03** (2022-05-18) ordered all U.S. federal civilian agencies to patch or remove affected VMware installations by 2022-05-24 — the same agencies that had just been told the same thing for CVE-2022-22954 six weeks earlier. Year discovered 2022, patched 2022.
- **References:** https://www.vmware.com/security/advisories/VMSA-2022-0014.html ; https://www.cisa.gov/news-events/directives/ed-22-03-mitigate-vmware-vulnerabilities ; https://www.rapid7.com/blog/post/2022/05/19/cve-2022-22972-critical-authentication-bypass-in-vmware-workspace-one-access-identity-manager-and-vrealize-automation/ ; https://www.assetnote.io/resources/research/understanding-cve-2022-22972-vmware-workspace-one-access-auth-bypass

### 6. CVE-2023-20887 — VMware Aria Operations for Networks (vRealize Network Insight) pre-auth command injection → RCE
- **Affected:** Aria Operations for Networks (formerly vRealize Network Insight / vRNI) 6.2 through 6.10.
- **Attack flow:** Two-issue chain — (a) reach the Apache Thrift endpoint exposed on the management interface despite no authentication, (b) inject shell metacharacters into a parameter passed to a `bash -c` invocation. Single unauth POST → root.
- **Root cause:** Thrift RPC endpoint exposed without auth + downstream shell-string composition with user input.
- **Disclosure:** Reported by Sina Kheirkhah (@SinSinology) of Summoning Team to ZDI; advisory VMSA-2023-0012 published 2023-06-07. Public PoC released same week. **CISA KEV:** added 2023-06-22 after observed in-the-wild exploitation. Year discovered 2023, patched 2023.
- **References:** https://www.vmware.com/security/advisories/VMSA-2023-0012.html ; https://summoning.team/blog/vmware-vrealize-network-insight-rce-cve-2023-20887/ ; https://blogs.juniper.net/en-us/threat-research/cve-2023-20887-vmware-aria-operations-for-networks-unauthenticated-remote-code-execution ; https://github.com/sinsinology/CVE-2023-20887

### 7. CVE-2023-34048 — vCenter Server DCERPC pre-auth out-of-bounds write → RCE (APT-exploited zero-day)
- **Affected:** vCenter Server 7.0 < 7.0 U3o, 8.0 < 8.0 U1d/U2b; VMware Cloud Foundation bundles.
- **Attack flow:** Unauthenticated network actor sends a crafted DCE/RPC packet to the vmdir/vmafd service → out-of-bounds write in the DCE/RPC protocol implementation → memory corruption → code execution. Forensic tell: `vmdird` crashes shortly before backdoor deployment.
- **Root cause:** OOB write in DCE/RPC marshalling layer of vCenter management services.
- **Disclosure:** Reported by Grigory Dorodnov of Trend Micro ZDI (publication ZDI-23-1623, suggesting a paid ZDI submission — bounty undisclosed). Advisory VMSA-2023-23 published 2023-10-24. **Mandiant** later attributed in-the-wild exploitation to **UNC3886** (China-nexus espionage) since late 2021 — a ~1.5-year zero-day window before patch. **CISA KEV:** added 2024-01-22. Year discovered 2023 (patched), exploited since 2021.
- **References:** https://www.vmware.com/security/advisories/VMSA-2023-0023.html ; https://www.zerodayinitiative.com/advisories/ZDI-23-1623/ ; https://cloud.google.com/blog/topics/threat-intelligence/chinese-vmware-exploitation-since-2021/ (Mandiant) ; https://www.bleepingcomputer.com/news/security/chinese-hackers-exploit-vmware-bug-as-zero-day-for-two-years/

### 8. CVE-2024-37085 — ESXi Active Directory integration "ESX Admins" auth bypass (ransomware-favorite)
- **Affected:** ESXi 7.0 < ESXi70U3q-24585291, ESXi 8.0 < ESXi80U3-24022510; vCenter-managed clusters where ESXi is joined to AD.
- **Attack flow:** Attacker with sufficient AD rights creates (or re-creates after deletion) a group literally named `ESX Admins` and adds an account. ESXi auto-grants every member full admin rights without checking that the group existed at join time. End-to-end: AD foothold → group create → SSH/API root on every domain-joined ESXi host → mass VM encryption.
- **Root cause:** Hard-coded trust of group name `ESX Admins` with no domain-scoped identity validation.
- **Disclosure:** Reported by Microsoft Threat Intelligence; advisory VMSA-2024-0013 published 2024-06-25. **Microsoft Security Blog** documents pre-patch exploitation by **Storm-0506 (Black Basta), Storm-1175, Octo Tempest, and Manatee Tempest** ransomware operators — including a confirmed Black Basta deployment at a North American engineering firm. **CISA KEV:** added 2024-07-30. Year discovered 2024 (exploited as 0-day), patched 2024.
- **References:** https://www.vmware.com/security/advisories/VMSA-2024-0013.html ; https://www.microsoft.com/en-us/security/blog/2024/07/29/ransomware-operators-exploit-esxi-hypervisor-vulnerability-for-mass-encryption/ ; https://www.rapid7.com/blog/post/2024/07/30/vmware-esxi-cve-2024-37085-targeted-in-ransomware-campaigns/ ; https://thehackernews.com/2024/07/vmware-esxi-flaw-exploited-by.html

### 9. CVE-2024-22273 — ESXi / Workstation / Fusion / vCenter storage controller OOB read/write
- **Note on the original ticket:** This CVE was listed in the brief as "Aria SSRF," but the actual NVD record describes an **ESXi/vCenter storage controller out-of-bounds read/write**, not an Aria SSRF. The closest Aria SSRF-adjacent issue in the 2024 cycle is **CVE-2023-34063** (VMSA-2024-0001) — Aria Automation missing access control allowing authenticated cross-org access; CVSSv3 9.9. Both are cited so the matrix is technically accurate.
- **Affected (CVE-2024-22273):** ESXi 7.0/8.0, Workstation 17.x, Fusion 13.x. vCenter Server packaged variants. Requires VM-local access with storage controllers enabled.
- **Attack flow:** VM with storage controllers enabled can issue crafted I/O to trigger OOB read/write on the host → information disclosure or DoS of the host (escape not directly demonstrated). CVSS 8.1 (Important).
- **Root cause:** Missing bounds check in the storage controller emulation path.
- **Disclosure:** Reported by Hao Zheng (@zhz) and Jiaqing Huang (@s0duku) of TianGong Team, Legendsec @ Qi'anxin Group. Advisory VMSA-2024-0011 published 2024-05-21. Year discovered 2024, patched 2024.
- **References:** https://www.vmware.com/security/advisories/VMSA-2024-0011.html ; https://nvd.nist.gov/vuln/detail/CVE-2024-22273 ; https://www.rapid7.com/db/vulnerabilities/vmsa-2024-0011-cve-2024-22273/
- **Aria-specific companion — CVE-2023-34063 (VMSA-2024-0001):** Aria Automation 8.11.x–8.14.x missing access control — authenticated actor obtains unauthorized cross-organization access to remote workflows. CVSSv3 9.9. Patched in Aria Automation 8.16. References: https://www.vmware.com/security/advisories/VMSA-2024-0001.html ; https://www.cisa.gov/news-events/alerts/2024/01/17/vmware-releases-security-advisory-aria-automation

### 10. CVE-2020-3992 + CVE-2021-21974 — ESXi OpenSLP pre-auth use-after-free / heap overflow (ESXiArgs ransomware vector)
- **Affected:** ESXi 6.5, 6.7, 7.0 prior to the OpenSLP patches (ESXi70U1c-17325551 / ESXi670-202102401-SG / ESXi650-202102101-SG). OpenSLP service on TCP/427.
- **Attack flow:** Unauth attacker sends a crafted SLP packet to port 427 → memory corruption in the SLP daemon → code execution as root on the hypervisor. CVE-2020-3992 is the use-after-free (VMSA-2020-0023); CVE-2021-21974 is the heap-overflow variant (VMSA-2021-0002, same release wave as 21972).
- **Root cause:** OpenSLP daemon — long-deprecated, exposed by default until 2021 — has unsafe parsing of SLP message frames.
- **Disclosure:** CVE-2020-3992 reported by Lucas Leong of Trend Micro ZDI (ZDI-20-1376, paid ZDI submission). CVE-2021-21974 reported by Lucas Leong of Trend Micro ZDI as well. **CISA KEV:** CVE-2020-3992 added 2021-11-03; CVE-2021-21974 added 2023-02-08. **ESXiArgs ransomware campaign** (Feb 2023) hit ~3,800 internet-exposed hosts via CVE-2021-21974 — two years after patch was available. VMware disabled SLP by default in subsequent releases. Year discovered 2020/2021, patched 2020/2021, mass-exploited 2023.
- **References:** https://www.vmware.com/security/advisories/VMSA-2020-0023.html ; https://www.vmware.com/security/advisories/VMSA-2021-0002.html ; https://www.zerodayinitiative.com/advisories/ZDI-20-1376/ ; https://www.cisa.gov/known-exploited-vulnerabilities-catalog ; https://www.bleepingcomputer.com/news/security/massive-esxiargs-ransomware-attack-targets-vmware-esxi-servers-worldwide/ ; https://www.recordedfuture.com/blog/esxiargs-ransomware-targets-vmware-esxi-openslp-servers

### Bonus: CVE-2022-31656 — Workspace ONE Access / Identity Manager / vRealize Automation auth bypass (post-22972 follow-up)
- **Affected:** Same product matrix as 22954/22972. Workspace ONE Access 21.08.x; Identity Manager 3.3.3–3.3.6; vRealize Automation 7.6.
- **Attack flow:** Network-only actor obtains admin without authenticating; chained with CVE-2022-31659 (auth'd RCE) the pair yields pre-auth admin RCE — the spiritual successor to the 22954+22972 pair.
- **Root cause:** Local-domain auth flow trusted a parameter that could be supplied without prior auth.
- **Disclosure:** Reported by **PetrusViet** of VNG Security; advisory VMSA-2022-0021 published 2022-08-02. PetrusViet released chain writeup + PoC. Year 2022.
- **References:** https://www.vmware.com/security/advisories/VMSA-2022-0021.html ; https://www.greynoise.io/blog/vmware-workspace-one-vulnerabilities-cve-2022-31656-and-cve-2022-31659 ; https://attackerkb.com/topics/RuMGC8Q1pE/cve-2022-31656

---

