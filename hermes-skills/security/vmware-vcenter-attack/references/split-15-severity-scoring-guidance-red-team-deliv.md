## Severity scoring guidance (red-team deliverable context)

| Finding | Severity |
|---|---|
| vCenter on internet, current patch | Informational (attack surface note) |
| vCenter on internet, missing patches with public RCE | **Critical** (entire virtualization plane compromise) |
| vCenter on internet + default admin password | **Critical** (immediate full takeover) |
| Workspace ONE on internet, unpatched 22954 | **Critical** |
| MOB anonymously accessible | **High** (full topology disclosure) |
| /sdk reachable + version disclosure only | **Medium** (info disclosure + attack-surface concentration) |

---

