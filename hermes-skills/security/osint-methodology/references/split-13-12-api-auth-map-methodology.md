## 12. API & Auth-Map Methodology

Modern targets expose REST, GraphQL, and undocumented internal APIs. The OSINT goal is to enumerate them, classify them, and rank by attack interest.

### 12.1 Discovery paths

- **Swagger / OpenAPI** — probe a 28-path wordlist (companion skill §16.1) on every alive webapp. Parse YAML/JSON; extract every endpoint (method + path).
- **GraphQL** — probe a 13-path wordlist (companion skill §16.2). POST a standard introspection query. If schema returns, you have full type/query/mutation/subscription enumeration.
- **GraphQL when introspection is disabled** — fall back to field-suggestion enumeration (companion skill §22.9).
- **Postman** — query Postman's public universal-search endpoint with the target name; walk each matching workspace; extract requests, headers, pre-request scripts, test scripts, env vars.
- **JS-extracted endpoints** — every endpoint extracted from JavaScript bundles feeds into the same classifier.
- **Mobile-extracted endpoints** — every endpoint from APK static analysis feeds in via sidecar (`mobile_endpoints.json`).

### 12.2 Classification

For each endpoint, capture:

```
url, method, source[], auth_required, auth_type, auth_location,
rate_limited, cors_policy, sensitive_path_keywords[], schema_leaks,
verb_tampering_possible, interest_score (0..100), interest_reasons[]
```

How to determine each field:
- Send `OPTIONS` → `Allow` header reveals supported methods (verb tampering check).
- Send `GET` without auth → 200 = `auth_required=false`; 401/403 = `auth_required=true`.
- Capture response headers for `WWW-Authenticate` (auth_type), `RateLimit-*` / `X-RateLimit-*`.
- Send a request with `Origin: https://attacker.example` → response `Access-Control-Allow-Origin` reflected = `cors_policy=reflected`.
- Trigger an error → check response for stack traces, ORM hints.

### 12.3 Interest score (0–100)

See companion skill §20 for the full rubric. **Score ≥ 70 → HIGH/CRITICAL finding** with `attack_path_hint` in evidence.

### 12.4 Attack-path hints

When emitting a HIGH/CRITICAL finding, include a one-sentence attack-path hint in the evidence so the operator knows where to start exploiting. Templates in companion skill §39.

---

