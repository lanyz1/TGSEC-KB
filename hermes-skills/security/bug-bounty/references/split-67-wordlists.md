## Wordlists
- [SecLists]([upstream-repo]) -- Comprehensive wordlists
- [HowToHunt]([upstream-repo]) -- Step-by-step vuln hunting
- [DefaultCreds]([upstream-repo]) -- Default credentials

- **`bug-bounty`** — When the user wants general bug-bounty guidance rather than tool location. Workflow primitive: `bug-bounty` is the orchestrator and routes to topic-matched hunt-* skills; this skill (`bb-local-toolkit`) answers "where is the tool / wordlist / clone on disk for that hunt?"
- **`web2-recon`** — When recon needs to be run via specific tool invocations. Workflow primitive: this skill names the local install path (e.g., `~/tools/SecretFinder/.venv/bin/activate`); `web2-recon` is the pipeline that strings those tool paths together.
- **`offensive-osint`** — When the operational arsenal (probes, regexes, wordlists) needs a tool to execute it. Workflow primitive: `offensive-osint` provides the regex / probe; this skill provides the local trufflehog / jhaddix / SecLists clone that runs it.
- **`security-arsenal`** — When the payload library needs a tool to fire payloads at scale. Workflow primitive: `security-arsenal` is the payload syntax; this skill names the ffuf / dalfox / ghauri install that delivers them.
- **`bb-methodology`** — When Phase 1 (Recon) or Phase 3 (Discovery) needs tooling routed. Workflow primitive: `bb-methodology`'s "Tool Routing by Phase" table is general; this skill resolves the abstract tool names to concrete local paths.
