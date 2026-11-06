## 13. JavaScript Deep Analysis

For every alive webapp, scrape its JS — it's where modern frontends leak.

### 13.1 Script discovery

- Parse HTML for `<script src="...">` and `<link rel="modulepreload" href="...">`.
- Probe a guess-path list (companion skill §16.9) for common bundlers.

### 13.2 Sourcemap detection (HIGH info disclosure)

- Inline reference: regex `//[#@]\s*sourceMappingURL=` at end of bundle.
- Sibling fetch: try `<bundle>.map` next to every discovered JS.
- If accessible: parse the sourcemap's `sources[]` (leaks repo structure) and `sourcesContent[]` (full original source code embedded). Run the secret catalog over `sourcesContent[]`.
- Severity: HIGH `INFO_DISCLOSURE`.

### 13.3 Secret scanning

Run the 29+-pattern catalog (companion skill §17) over every JS body and every parsed `sourcesContent[]` blob. Each hit = `SECRET_LEAK` finding with the catalog's per-pattern severity.

### 13.4 Endpoint extraction

Three regex tiers (companion skill §16.10). Each unique endpoint becomes a `wayback_endpoint` asset and feeds into the API classifier in §12.

### 13.5 Internal-host leakage detection

Three patterns (companion skill §16.11): RFC1918, internal DNS suffixes, K8s service DNS. Each match = MEDIUM `INFO_DISCLOSURE`.

### 13.6 GraphQL introspection probe

When an extracted endpoint ends in `/graphql` or `/graphiql`, POST the standard introspection query. If schema returns → HIGH `MISCONFIG`. Then enumerate mutations and subscriptions for high-value targets.

### 13.7 Next.js manifest parsing

`_buildManifest.js` and `_ssgManifest.js` enumerate every Next.js page route — exposes the application's full route structure.

### 13.8 Budget guidelines

- Cap webapps analyzed per engagement: 40 default, 120 with `--deep`.
- Cap JS files per webapp: 40 default, 80 with `--deep`.
- Cap individual JS file size: 2 MiB.
- Per-file timeout: 10 seconds.

---

