## Step 5 — Default credentials (frequently still valid on lab/staging vCenters)

| Product | Default user | Default password |
|---|---|---|
| vCenter 6.x | `<EMAIL-REDACTED>` | `<set-during-install>` |
| vCenter Appliance root | `root` | `vmware` (legacy) or `<set>` |
| ESXi root | `root` | `<blank>` or `vmware` |
| vCenter Server Appliance Mgmt (5480) | `root` | `<set-during-install>` |
| Aria Operations | `admin` | `vmware` (legacy) |
| Workspace ONE | `admin` | `<set>` |

⚠ **Do not spray vCenter — `<EMAIL-REDACTED>` has VERY low lockout threshold** (often 3 attempts → 60s lockout, configurable to permanent). One attempt with high-confidence guess only. Use creds discovered in breach corpora.

---

