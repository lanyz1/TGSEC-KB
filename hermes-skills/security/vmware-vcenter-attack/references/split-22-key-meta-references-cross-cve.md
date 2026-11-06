## Key meta-references (cross-CVE)

- **CISA KEV catalog (VMware filter):** https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=vmware — VMware is one of the most-represented vendors; cross-check any vCenter/ESXi/Workspace finding here before grading severity.
- **Broadcom (formerly VMware) advisories index:** https://support.broadcom.com/security-advisories (legacy https://www.vmware.com/security/advisories.html). Search by VMSA-YYYY-NNNN.
- **ZDI published advisories:** https://www.zerodayinitiative.com/advisories/published/ — filter "VMware" for the canonical paid-bounty disclosures (CVE-2020-3992, CVE-2023-34048, multiple Aria Operations and vRNI).
- **Mandiant UNC3886 reporting:** Google Cloud Threat Intelligence has the deepest published forensic trail on long-tail vCenter zero-day exploitation. Pair with the `mid-engagement-ir-detection` skill when working a target where vCenter is reachable.

The pattern across every entry above: **VMware management-plane CVEs are pre-auth, network-reachable, and mass-exploited within days of patch.** When external recon surfaces any of these products at a current-minus-one patch level, that is a Critical finding worth a same-day callout in the deliverable — not a Medium info-disclosure.
