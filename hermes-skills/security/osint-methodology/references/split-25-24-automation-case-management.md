## 24. Automation & Case Management

### 24.1 Tools

Hunchly, Kasm Workspaces, ArchiveBox, SingleFileZ.

### 24.2 Cross-Module Coordination Patterns

When multiple OSINTtools (or modules) run, late-arriving outputs need to feed into earlier-running consumers. Three patterns:

1. **Sidecar JSON drops** — module writes `<scan>/mobile_endpoints.json` or `<scan>/secrets_sidecar.json`; later modules read on start. No blocking.
2. **Asset-graph upserts** — shared graph store; new assets trigger downstream modules via event bus.
3. **Late-binding queues** — long-running enumeration emits assets continuously; enrichment workers pull.

In ad-hoc engagement: `tmpdir + JSON sidecars + one-line manifest` makes operations composable.

### 24.3 Multi-Engine Corpus Run Methodology

Running a large dork corpus across multiple engines:

- **Pluggable engines** — wrap each engine (DDG, Bing, Brave, SerpAPI, Yandex, Baidu) behind a common interface. Default DDG (keyless); fall back to others when keys available.
- **Per-engine rate-limiting** — each engine has its own quota and ban posture. Use a token bucket per engine.
- **Result classification** — URL-signature → title-hint → snippet-regex pipeline. Output: `(severity, category, confidence)`.
- **Dedup by URL** — different engines surface duplicates.
- **Confidence rule** — snippet-only = TENTATIVE.
- **Persistence** — corpus DB so re-runs across engagements deduplicate.

### 24.4 Evidence Preservation for Offensive Engagements

- Per-engagement / per-scan SQLite store.
- JSONL run log with `run_id`, every event one line, UTC timestamps,command-line versions.
- SHA-256 every downloaded artifact.
- PNG screenshots.
- Raw HTTP requests/responses, capped at 2 KiB body per side.
- Evidence served read-only from operator's machine.
- Reproduction package: `run_id` +command-line versions + JSONL log + asset/findings DB.

---

