## 8. Asset Graph Discipline

Treat every discovery as a typed asset in a graph, not a free-floating string.

### 8.1 Asset Taxonomy (29 types)

| Category | Asset Types |
|---|---|
| **DNS / Network** | `domain`, `subdomain`, `ip`, `netblock`, `asn` |
| **Service** | `port`, `service`, `certificate` |
| **Identity** | `email`, `person`, `credential` |
| **Code / Config** | `repo`, `secret` |
| **Cloud / Storage** | `bucket`, `firebase_project` |
| **Web** | `webapp`, `wayback_endpoint`, `api_endpoint`, `api_spec`, `graphql_schema` |
| **Mobile** | `mobile_app`, `deep_link`, `exported_component` |
| **Phishing / Adversarial** | `typosquat_domain` |
| **Collaboration / SaaS** | `postman_collection`, `postman_workspace`, `postman_api_key`, `stack_post`, `saas_public_surface` |

### 8.2 Asset Schema

Every asset carries:
- `type` — one of the 29 above.
- `key` — unique dedup id (typed prefix, e.g. `sub:api.example.com`, `email:<EMAIL-REDACTED>`).
- `value` — the actual string/object.
- `sources[]` — every source that confirmed this asset (deduplicated).
- `confidence` — TENTATIVE / FIRM / CONFIRMED.
- `first_seen`, `last_seen` — UTC timestamps.
- `attrs{}` — type-specific metadata (e.g., for a `webapp`: status_code, title, tech-stack list, JARM, favicon mmh3, screenshot path).

### 8.3 Edge Taxonomy

Relationships are typed edges, not text:
`RESOLVES_TO`, `HOSTED_ON`, `IN_NETBLOCK`, `BELONGS_TO_ASN`, `LISTED_IN_CERT`, `OWNED_BY`, `ALIAS_OF`, `BREACHED_FROM`, `EMPLOYED_BY`, `HOSTS_REPO`, `TYPOSQUAT_OF`, `EXPOSES`, `DOCUMENTED_BY`, `BELONGS_TO_HOST`, `REQUIRES_AUTH`, `LEAKS_SCHEMA`, `SHIPPED_BY_ORG`, `CONTAINS_SECRET`, `TALKS_TO_HOST`, `EXPOSES_DEEPLINK`, `HAS_EXPORTED_COMPONENT`, `USES_FIREBASE_PROJECT`, `LACKS_PINNING_FOR`.

### 8.4 Discipline rules

- **Every discovery is an asset.** Don't write findings against free-floating strings; create the asset first, then attach the finding.
- **Dedup by key, not by value.** Same value, different type ≠ same asset (`sub:api.example.com` and `webapp:https://api.example.com/` are different assets with a `BELONGS_TO_HOST` edge).
- **Provenance is non-negotiable.** `sources[]` must list every source. If two sources confirmed it, both go in.
- **Confidence is per-source, then aggregated.** A subdomain returned by 3 passive sources is FIRM; one returned by snippet-only Bing is TENTATIVE.
- **Late binding via sidecars.** When module A produces output that module B needs, write a JSON sidecar (`mobile_endpoints.json`, `secrets_sidecar.json`) — don't block module B on module A. See §24.

### 8.5 Asset-Level Triage Rules

When you have a mixed bag of assets and limited probe budget, prioritize by what each asset *enables*:

**WebApp priority by hostname signal (highest first):**

1. Auth-related hostnames (`auth.`, `login.`, `sso.`, `idp.`, `accounts.`, `oauth.`).
2. Admin paths (`/admin`, `/dashboard`, `/console`, `/manager`, `/wp-admin`, `/phpmyadmin`).
3. Dev/staging hosts (`dev.`, `staging.`, `stg.`, `qa.`, `uat.`, `test.`, `sandbox.`, `preprod.`, `preview.`) — lower defenses, often dump prod data.
4. API hostnames (`api.`, `services.`, `gateway.`, `graph.`).
5. Customer-facing hostnames (`portal.`, `app.`, `my.`, `account.`).
6. Marketing / content (`www.`, `blog.`, `news.`, `careers.`, `support.`).

**Subdomain priority by inferred function:**

- API > Admin > Dev > Auth > Prod-app > Marketing.

**IP priority by netblock:**

- Corporate ASN-owned (most likely to host unadvertised internal infra).
- Cloud netblocks (AWS / GCP / Azure / DO / OVH) — high turnover but interesting for cloud-native services.
- CDN ranges (Cloudflare / Akamai / Fastly) — usually edge, not origin; defer unless doing origin discovery.

**Email priority by role hint:**

| Role indicator | Priority | Why |
|---|---|---|
| `ceo@`, `cfo@`, `cto@`, `ciso@` | HIGHEST | Exec accounts have highest breach value (BEC, finance authority, board access). |
| `it@`, `helpdesk@`, `support@`, `security@` | HIGH | IT/security accounts have privileged command-line access; helpdesk accounts handle reset workflows. |
| `dev`, `engineer`, `architect`, `dba` | MEDIUM | Developer accounts often have GitHub / cloud / CI access. |
| `sales`, `marketing`, `hr`, `finance` | MEDIUM | SaaS access (Salesforce, HubSpot, Workday); finance enables BEC. |
| Generic role accounts (`info@`, `noreply@`, `contact@`) | LOW | Often unmonitored or alias forwarded; less personal context. |

**Repo priority by recency + naming:**

- Recently-pushed (last 30 days) > stale.
- Public repo with target name in description > target name only in code.
- Forked from internal-looking parent > standalone.
- Mentions `prod`, `internal`, `private`, `secret` in name → priority HIGH despite being public (may be misnamed or accidentally exposed).

**Application order:** when you have N assets and budget for M probes (M < N), apply asset-type priority first, then within-type priority. E.g.: 50 subdomains → probe API + admin + dev first (~15), then auth + prod-app (~20), defer marketing/content to a later pass.

---

