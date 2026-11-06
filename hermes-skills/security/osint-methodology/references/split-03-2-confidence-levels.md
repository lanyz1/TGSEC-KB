## 2. Confidence Levels

Every assertion you make during an engagement should carry a confidence level. Three levels:

| Level | Meaning | Examples |
|---|---|---|
| **TENTATIVE** | Plausible based on indirect evidence; unverified. | Snippet-only Google dork match; email pattern inferred from name; subdomain returned by one passive source only; favicon-hash overlap (two hosts share a favicon — could be shared infra, could be a coincidence). |
| **FIRM** | Directly observed but uncorroborated. | Subdomain that resolves to an IP; HEAD-confirmed bucket exists (private); CT-log entry shows certificate; Shodan banner returned. |
| **CONFIRMED** | Multiple independent corroborations OR directly verified. | Live-validated PMAK token (read-only `/me` returned 200); breach corpus + crt.sh + DNS all agree; bucket listable AND files retrievable; user enumerated AND password reset flow returns valid hint. |

**Rule of three for attribution:** require three independent weak signals, OR one strong + one weak, before asserting linkage. Don't single-source attribute.

### 2.1 Confidence Upgrade Workflows

Confidence isn't static — every TENTATIVE asset should have a documented path to FIRM and to CONFIRMED. Use these per-asset-type rules.

| Asset type | TENTATIVE → FIRM | FIRM → CONFIRMED |
|---|---|---|
| **Subdomain** | Returned by ≥2 independent passive sources, OR DNS A/AAAA/CNAME resolves successfully. | Serves on a standard port (80/443/22/etc.) AND HTTP banner / TLS cert / SSH banner returned. |
| **IP** | Discovered via ≥2 sources (passive DNS, ASN lookup, Shodan). | Active probe responds (TCP SYN-ACK on at least one port, or ICMP echo reply). |
| **WebApp** | URL extracted from JS / API / archive but not yet hit. | HTTP request returns 2xx/3xx/4xx (any non-network-error response) AND content-length > 0. |
| **Email** | Generated from a name pattern OR returned by snippet-only dork. | Listed in Hunter.io / EmailRep / IntelX / breach corpus, OR `MAIL FROM`/`RCPT TO` SMTP probe returns 250 (without delivery — abort at DATA). |
| **Bucket (S3/GCS/Azure)** | Permutation candidate; no probe yet. | HEAD returns 200, 301, or 403 (existence confirmed). Then CONFIRMED when GET returns object listing or known object retrieval. |
| **Endpoint (API / wayback)** | Extracted from JS regex / Wayback / Postman. | HTTP request returns non-404 (route exists). Then CONFIRMED when the endpoint's behavior is fingerprinted (auth posture, response shape, rate limits). |
| **Credential / secret** | Matches catalog regex in captured text. | Read-only validator (`/me`, `auth.test`, `sts:GetCallerIdentity`, `/user`) returns success. Then CONFIRMED with documented scope + account ID. |
| **Person** | Name extracted from a single source (LinkedIn / breach / GitHub commit). | Confirmed by a second source (Hunter.io role + LinkedIn profile, or two breach sources with same email). |
| **Repo** | Name match on org keyword in GitHub search. | Repo metadata shows confirmed org/email/website match. Then CONFIRMED when commit-history shows employee involvement. |
| **Mobile app** | Name match in app store. | Ownership-confidence score ≥70 (see companion skill §21). Then CONFIRMED when binary metadata (signing cert, package name, dev account) ties back to target. |
| **Certificate** | Returned by crt.sh once. | CT-log entry confirmed in ≥2 logs. Then CONFIRMED when serving on a discovered host. |
| **SSO tenant** | Discovery-endpoint returns OIDC metadata. | Tenant GUID extracted AND domain resolves through the tenant's expected MX / autodiscover / SP record. |

**Default reporting posture:** never claim CONFIRMED without explicit corroboration. When in doubt, downgrade. Operators trust under-claims more than over-claims.

---

