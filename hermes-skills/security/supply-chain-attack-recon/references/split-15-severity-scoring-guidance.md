## Severity scoring guidance

| Finding | Severity |
|---|---|
| Internal package name + no scope-mapping + unclaimed on public npm + actively in builds | **Critical** — Dep-confusion RCE |
| Internal package name + scope-mapping in `.npmrc` but `_authToken` leaked | **Critical** — direct registry push |
| Pull_request_target workflow + secrets exposed + PR-controlled code execution | **Critical** — Org-wide token theft |
| Docker image with leaked secret in layer | **High** (varies by secret) |
| Internal registry URL disclosed (but no creds) | **Low** — Info-disc only |
| Typosquat candidate identified (not published) | **Informational** — Awareness item |
| Public org has 1000+ unused names that COULD be claimed | **Informational** — Hygiene |

---

