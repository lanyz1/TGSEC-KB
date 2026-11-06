## Pitfalls
- **SharePoint version disclosure without CVE** — knowing the SP version is informational. Need a matching exploitable CVE.
- **/_layouts/ accessible but no anonymous operations** — path reachability is recon. Need anonymous read/write/execute.
- **EoL SharePoint without exploitation** — "SharePoint 2013 is EoL" is a hygiene finding, not a vulnerability. Need demonstrated exploit.
- **FormDigest anonymous issuance** — `_api/contextinfo` returning FormDigest anonymously is a precondition for ToolShell, not a standalone bug.
- **Modern vs Classic auth** — SharePoint Online uses Modern Auth (OAuth). On-prem SP may use Classic (NTLM/Kerberos). Different attack surfaces.

---

