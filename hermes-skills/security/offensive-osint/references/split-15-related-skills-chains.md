## Related Skills & Chains

- **`web2-recon`** — When the arsenal needs to be executed against a live host set. Workflow primitive: this skill provides the probe paths and wordlists; `web2-recon` runs the actual subfinder → dnsx → httpx → katana pipeline that consumes them.
- **`osint-methodology`** — When this skill's concrete probes need a planning framework. Workflow primitive: `osint-methodology` is the planning skeleton (5-stage pipeline, asset graph, findings rubric); this skill is the operational arsenal that fills each stage with curl one-liners and regexes.
- **`hunt-subdomain`** — When this skill's subdomain enumeration finds stale CNAMEs. Workflow primitive: subdomains discovered via §27 / `references/recon-stack.md` get auto-routed to `hunt-subdomain` for takeover validation.
- **`hunt-cloud-misconfig`** — When this skill's cloud-bucket enum surfaces listable buckets / Firebase / actuator endpoints. Workflow primitive: §39 attack-path hints (listable bucket, /actuator/env, open Elasticsearch) hand off to `hunt-cloud-misconfig` for exploitation.
- **`m365-entra-attack`** / **`okta-attack`** — When identity-fabric fingerprinting finds Entra/Okta. Workflow primitive: `references/identity-fabric.md` fingerprints the IdP; matched platform skill (loaded by `hunt-dispatch`) takes over for active enumeration.
