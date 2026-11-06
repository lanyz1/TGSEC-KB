## Related Skills & Chains

- **`hunt-saml`** — vCenter Workspace ONE / VMware Identity Manager publishes SAML SP metadata at `/SAAS/API/1.0/GET/metadata/idp.xml` and consumes assertions at predictable ACS URLs. Chain primitive: vCenter SAML SP metadata reachable → IdP fingerprinted → `hunt-saml` XSW1-XSW8 against the federating IdP → forged assertion with `userPrincipalName=<EMAIL-REDACTED>` → SP-impersonation as vCenter admin → full virtualization-plane takeover.
- **`hunt-rce`** — VMware's high-impact CVE catalog (CVE-2021-21972, CVE-2021-21985, CVE-2022-22954, CVE-2023-20887) is almost entirely pre-auth RCE. Chain primitive: vCenter version fingerprint via SSL banner or `/ui/login` body → confirm patch level missing → `hunt-rce` deserialization/SSTI gadget from the matching CVE PoC → `root` on vCenter appliance → API-token mint → cluster-wide VM control.
- **`enterprise-vpn-attack`** — VPN compromise + vCenter on internal-only is a natural post-VPN pivot, but external-only engagement scope sometimes forbids it. Chain primitive: VPN appliance CVE → foothold inside corp network → if scope permits, `vmware-vcenter-attack` becomes reachable on internal-only vCenter → datacenter takeover.
- **`m365-entra-attack`** — Some VMware deployments federate vCenter SSO to Entra. Chain primitive: vCenter SSO discovery → AuthURL points to `login.microsoftonline.com` → `m365-entra-attack` Entra ATO on `<EMAIL-REDACTED>` synced identity → SAML assertion → vCenter admin without ever brute-forcing vCenter SSO.
- **`mid-engagement-ir-detection`** — VMware vSAN/vCenter alerting is sensitive; expect SOC to patch or block within hours of detection. Chain primitive: confirmed vCenter CVE → run `mid-engagement-ir-detection` baseline capture BEFORE attempting exploitation → if response patterns change mid-test, capture the SOC-patched state as a SECOND finding (defensive-action observed). Package both via `redteam-report-template`.

---

