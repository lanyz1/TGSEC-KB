## Pitfalls
- **vCenter version disclosure without CVE** — knowing the vCenter version is recon. Need a pre-auth CVE affecting that specific version.
- **Post-exploitation assumed** — vCenter attacks typically require initial foothold. The finding is what you can do ONCE inside, not how you got there.
- **ESXi vs vCenter confusion** — vCenter manages ESXi hosts. Attacking vCenter gives you the whole cluster. Attacking one ESXi host gives you one box.
- **VM escape complexity** — VM escape from a guest to the hypervisor is extremely difficult. Focus on vCenter credential theft first, VM escape second.
- **SSO domain administrator** — vCenter SSO `<EMAIL-REDACTED>` has unlimited power. This account is the primary target.
- **Log insight / vRealize** — vCenter add-ons (Log Insight, vRealize Operations) have their own CVEs. Don't stop at the vCenter web UI.


---

