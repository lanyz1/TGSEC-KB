# Corpus → external resources: working patterns

Extracted from a large engagement where ticket-corpus mining kept paying beyond credentials.

## GitHub org discovery & public repos

```bash
# 1) find org/repo refs in the corpus
grep -rhoE 'github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' corpus/ | sort | uniq -c | sort -rn | head
# 2) enumerate the org's PUBLIC repos (private ones 404 on clone/API)
curl -s 'https://api.github.com/orgs/<org>/repos?per_page=100&sort=updated'   # check 'fork' flag
# 3) shallow-clone the interesting ones
 git clone --depth 20 https://github.com/<org>/<repo>
```

What pays (validated):
- QA/automation suites (`*_automatedTests`, cypress/playwright repos) — plaintext logins for LIVE backoffice/staging systems, full URL maps of the product's routes.
- Official SDK/client repos — the protocol, signing scheme and endpoint map (e.g. a payment platform's official Python client + docs).
- Infra repos (terraform/helm/infra-clusters) — often private, but note names for later.
- Author emails in git log = staff identities (cross-check with staff rosters; personal Gmails of admins are notable).

## Google Docs / Sheets (anyone-with-link export)

Regex: `https://docs\.google\.com/(document|spreadsheets|presentation|file)/d/([A-Za-z0-9_-]{20,})`

```bash
curl -sL 'https://docs.google.com/spreadsheets/d/<id>/export?format=csv'    # 200 text/csv = public
curl -sL 'https://docs.google.com/document/d/<id>/export?format=txt'       # 200 text/plain = public
# login-walled docs redirect to accounts.google.com — skip those
```

Each sheet tab can have its own (also public) `gid`. In one corpus 36/145 linked docs were anonymously readable (game catalogs, settlement models, risk-scoring logic, test matrices).

## OneTimeSecret

Modern instances (eu./ca./nz.onetimesecret.com): any `/secret/<key>` URL returns the SPA shell regardless (no signal).

```bash
# real check: reveal endpoint (no CSRF needed via API)
curl -s -X POST 'https://<region>.onetimesecret.com/api/v2/secret/<key>/reveal' \
  -H 'Content-Type: application/json' -d '{"passphrase":""}'
# 200 = secret; 404 {"error_type":"RecordNotFound"} = consumed/expired (the common case for old tickets)
```

Old paths: `/api/v1/secret/` = 404; `POST /secret/<key>` without a CSRF session = 403. One check, then park.

## Ticket attachments (Shortcut example, generalizes)

Copy the live session cookies via CDP, then fetch the attachment URL directly:

```python
# CDP: Network.getCookies {"urls": ["https://app.shortcut.com", "https://media.app.shortcut.com"]}
# then requests.get(attachment_url, cookies={"sid": ...})
```

- Images feed the OCR pipeline; zips/txt/conf pay more.
- **ClickUp**: attachment hosts like `t<pod>.p.clickup-attachments.com` often serve the file with NO auth (public CDN) — fetch the link straight from the ticket JSON; 20-image batches are typical, OCR them.
- **SharePoint shares** (`<org>.sharepoint.com/:f:/...`): password-gated or revoked; one probe, park (the "Sharing Link Validation" / "This link has been removed" page is the tell).
- `.zip` attachments may be password-encrypted: `zipfile.read()` raises `RuntimeError("password required")`. Try a candidate list built from the ticket's own known strings (its creds, org name, project codes); no hit → park, don't brute.

## GitBook docs mirroring (docs.<host>)

```bash
curl -s https://docs.<host>/llms.txt            # full page index
curl -s https://docs.<host>/<page>.md           # any page as clean markdown
curl -s https://docs.<host>/llms-full.txt       # entire corpus in one file
# doc-grounded Q&A: GET <page>.md?ask=<question>&goal=<goal>
```

## OpenAPI spec hunt

On docs hosts try: `/openapi.json` `/swagger.json` `/api-docs` `/redoc` `/openapi.yaml` — `/openapi.json` hits often.

**Verify documented signing examples before writing client code** — recompute the published example (e.g. `hmac.new(key.encode(), body.encode(), sha256).hexdigest()` must equal the doc's example signature). This proves key/message order and encoding in one step.

## Object-storage leads (MinIO / S3 / cloud buckets)

Tickets leak storage endpoints three ways: CI/artifact conversations (`minio-artifacts.cicd.svc:9001` internal + `minio-artifacts.<domain>` web console), incident/compliance write-ups (which managed S3 an app moved to: Hetzner `fsn1.your-objectstorage.com`, OVH `s3.<region>.io.cloud.ovh.net`, AWS `s3.<region>.amazonaws.com`), and bucket names pasted next to config keys (`rozert-pay-exports`, `<app>-clickhouse-archive`).

Probe recipe:
```bash
# 1) web console: SPA catch-all returns the same HTML for every path — real API is /api/v1/*
curl -sk https://minio-artifacts.<domain>/api/v1/buckets        # 403 {"message":"access denied"} = live, auth-backed
# 2) default creds on the console API (1-2 tries max): POST /api/v1/login {"accessKey":"minioadmin","secretKey":"minioadmin"}
# 3) anonymous bucket sweep — status discrimination is the whole game:
#    NoSuchBucket = name free; AccessDenied = EXISTS; 200 = LISTABLE
curl -sk "https://<region-endpoint>/<bucket>/?list-type=2&max-keys=5"
#    OVH is virtual-host style: https://<bucket>.s3.uk.io.cloud.ovh.net/?list-type=2
#    Hetzner regions: fsn1 | nbg1 | hel1 .your-objectstorage.com (same bucket may exist on one region, not another)
```

**Scope discipline on shared endpoints**: cloud object-storage hostnames are shared by every customer of that region — a listable bucket like `reports` or `exports` may belong to an UNRELATED company. List 3-5 keys and classify the owner BEFORE any download; unrelated → stop immediately, log it, move on (example: a `reports` bucket turned out to be a cosmetics firm's regulatory PDFs — abandoned on first key). Private-but-existing buckets (`AccessDenied`) still confirm the bucket name — keep them in the lead list; credentials for them surface later (CI secrets, config dumps).

## Onboarding / invite templates reveal the gate stack

Greppable template text ("We created a user account for", "incognito mode", "log out at the end of the work day", "You will find … in the Vault") documents the REAL defense stack of prod portals without touching them: client certificate (mTLS) + credential delivery via zero-knowledge vault + portal URL that is (by design) NXDOMAIN externally. When the corpus shows this stack, stop probing the portal — the path in is the vault/CA, not the login form. Also note the staff alias convention in these tickets (`name.x+admin@domain`) for replay on lower envs.

## Vendor portals found in tickets

Entries like "BO user/pass", client-area logins, operator-portal accounts are TEST-worthy once each — they frequently still work after years and expose the target's own account scope. Login-probe specifics (Django trailing slash, WordPress wp-login, Keycloak password grant, Infisical) — see the `oss-deployed-app-audit` skill's `references/frontend-auth-probes.md`.
