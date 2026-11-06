---
name: ticketing-system-mining
description: "Use when mining helpdesk/ticketing systems for intel."
version: 0.1.0
tags: [intel, ticketing, shortcut, jira, zendesk, credentials, mining]
---

# Ticketing / Helpdesk System Mining

Use when an authenticated session (or creds) for the target's ticketing/helpdesk system is in scope (Shortcut, Jira/Confluence, Zendesk, Freshdesk, ServiceNow, Linear). These systems are one of the richest intel veins in an engagement: customer/player PII, infra runbooks, **pasted credentials in comments**, and attachments (screenshots of admin panels). Validated at scale: a Shortcut workspace swept end-to-end (tens of thousands of entities); admin credentials recovered from story comments and reused against live systems.

## Workflow

1. **Locate the private API.** Watch the network tab (or probe) while using the UI — authenticated SPAs call a JSON backend (Shortcut: `/backend/api/private/...`). Capture exact endpoints + custom headers (tenant/org headers are common; missing them → 403/404 even with a valid session).
2. **Drive it from the logged-in browser tab** (CDP): evaluate `fetch(url, {credentials:'include'})` *inside the page* so session cookies carry. Concrete pattern + minimal cdp.py helper: `references/shortcut-clubhouse.md`.
3. **Search-sweep for IDs — never brute IDs.** Search endpoint takes `query=` + page size (~100 max) + cursor. Run a term list: domain terms (brands, KYC, deposits, fraud, complaint…), infra terms (vault/kubeconfig/ssh/vpn/access/hosting…), credential terms (password/login/key/secret/creds — **in the org's own language too**, e.g. пароль/доступ/ключ/креды). Save `{id: name}` to `ids.json` after every term (resumable). Fresh term baskets keep paying big across waves (measured +500 → +672 → +1200 new IDs on successive baskets): infra (kubeconfig/kubectl/harbor/jenkins/gitlab/nexus/clickhouse/opensearch/kibana/prometheus/rabbitmq/ssh/pem/minio/s3), security-ops (whitelist/вайтлист/certificate/сертификат/otp/totp/bitwarden/1password/vaultwarden/nuclino/confluence/canary/healthcheck/release), and process verbs in the org's language (восстановлени/сброс/окружени).
4. **Fetch full entities** per ID: description + **comments** + tasks + files. Comments are where ops write runbooks ("invite sent"), temp passwords, and pasted creds. ~1 req/s; one JSON per entity on disk → re-runs idempotent, nothing lost.
5. **Regex-scan the corpus for credentials** — `scripts/cred_scan.py`: email/password adjacency, password/login keywords (multi-language), api/secret keys, token shapes (`st.*`, `hskey-*`, `tskey-*`, `sk-*`…). Dedupe fragments; review hits manually (false positives are cheap, misses aren't).
6. **Harvest attachments**: entity attachment URLs feed a download + OCR pipeline; ops screenshots leak admin panels, credential pages, internal tools.
7. **Roster endpoint** → staff emails for password-matrix / SSO work.

## Lead expansion (corpus → external resources)

The corpus maps the org's external footprint — mine it for leads, not just creds (command patterns: `references/corpus-lead-expansion.md`):

- **GitHub refs** (`github.com/<org>/…`): enumerate the org's **public** repos (`api.github.com/orgs/<org>/repos`), shallow-clone, scan. QA/automation suites routinely embed **working plaintext logins** for live backoffices; official SDK repos double as API documentation.
- **Google Docs/Sheets links**: anonymous-export test (`/spreadsheets/d/<id>/export?format=csv`, `/document/d/<id>/export?format=txt`) — anyone-with-link material exports without auth.
- **OneTimeSecret / share links**: usually consumed or revoked — one probe, park.
- **Non-image attachments**: download with live session cookies (CDP `Network.getCookies`); zips/configs pay; encrypted zips = quick candidate test only.
- **Docs subdomains**: GitBook sites mirror via `/llms.txt` + `.md` suffix + `/llms-full.txt`; hunt `/openapi.json` and verify documented signature examples by recomputation.
- **Storage endpoints** leaked in tickets (MinIO console/internal svc, managed-S3 hostnames + bucket names): anonymous bucket-sweep recipe (NoSuchBucket vs AccessDenied vs 200), region/vhost-style quirks and the shared-endpoint scope rule live in the reference — plus what **onboarding/invite templates** reveal about prod gates (mTLS cert + vault delivery).
- **Vendor portals** ("BO user/pass", client areas found in tickets): test once; login-probe specifics live in the `oss-deployed-app-audit` skill.

## What it pays for (validated categories)

- PII: support threads with phone numbers / emails in plain text (masked in the main DBs).
- Infra runbooks: how staff join the secrets vault, kube auth flows (`make kubeauth <user> TARGET_NAME=<cluster>`, "password in vault", WireGuard prerequisite), VPN provisioning, secret-manager migrations — names the keystone systems. **Grep-able artifacts to extract verbatim**: OIDC client-ids (`[0-9]{8,}-[a-z0-9]+\.apps\.googleusercontent\.com` — secrets usually sanitized `XXX`/"in vault", but the IDs still map the Google auth surface), `oidc-login get-token` kubeconfig blocks, `TARGET_NAME=` values = cluster inventory (dev/production-centro/rozert-pay/…), node rosters from pasted `kubectl get nodes`, and "Vault 非 SSO（白名单注册）"-type comments that pin which keystone accepts self-registration.
- **Pasted credentials**: admin email+password pairs in comments, "temporary password" handoffs, CI test creds — feed directly into login matrices for other systems.
- **密码管理器笔记（最肥的一类）**：员工把 Bitwarden/1Password『安全笔记』正文直接贴进工单（含 `password: X` 行），或只留引用（「креды в Bitwarden, заметка X」）——引用名 = 日后打保险库的目标清单。专扫词：bitwarden / vaultwarden / 1password + заметка / note / secure；本案 ~30 处命中、数条含可用口令（含一条 `password: <REDACTED> 类明文）。
- Attachments: screenshots of admin panels, exported spreadsheets, docs. **浏览器工具栏截图 = 内部工具清单**：员工截图里的标签页常带 Vaultwarden / TeamCity(CI) / 各 dashboard 名称 → 得内部主机名 + CI/密码库系统清单（再去 DNS 枚举、探 CI）。

## Pitfalls

- Entity JSON is often ONE multi-100KB line (comments inline) — parse with `json.load` in Python; line-based readers truncate badly.
- **Hand-replicating custom headers is a rabbit hole** (`x-requested-with`, tenant/context headers → 401 `organization context missing` without them). Faster path: **let the SPA make the calls and capture its own responses** — `page.on('response')`, filter URL + status 200 + JSON, save per entity (validated on Shortcut after hand-rolled fetches kept 401ing).
- **Sessions outlive the engagement**: before assuming fresh auth is needed, sweep local browser profiles' cookie DBs (`<profile>/Default/Cookies`, via python `sqlite3` — the CLI is often absent) for live logged-in domains; a months-old profile reopened the workspace cold.
- "в аттаче" / "see attached" text ≠ attachment present: `linked_files`/`files` arrays are often empty and media URLs 403/expired (years-old screenshots) — one probe, then move on.
- The driving browser tab can die (crash, housekeeping restart): make the loop reconnect its WebSocket, keep all progress id-keyed on disk.
- Don't fetch the whole ID universe blind — the search sweep selects relevance; the full fetch is the long, rate-limited phase.
- Search caps page size (~100) and repeats results across terms — paginate with the cursor, dedupe via setdefault.
- Credentials hide in comments far more than descriptions — don't skip thin descriptions.
- Sweep terms in the org's own language; English-only sweeps miss.
- Deep pagination over terms already covered saturates fast (measured: a full second paginated pass added only ~15% new IDs) — new coverage comes cheaper from new term families (aliases, sub-brands, second languages) than from deeper pages.
- Old share links are a class of dead end (OneTimeSecret, SharePoint shares) — almost always consumed/revoked; cap at one probe. **OneTimeSecret 实测探法**：页面 200 只是通用壳，不代表有货；`POST /api/v1/secret/<key> {"passphrase":""}` 才见真章——回 `Unknown secret` = 已消费/过期（实测 10/10 全灭），有货再继续。**Bitwarden Send（`<vault-host>/#/send/<accessId>/<key>`）**：解密键在 URL fragment、客户端解密——实例活着即免登录可看；先解析域名（停用/已删域名 = NXDOMAIN 秒判死），域名活着再开浏览器读渲染文本。
- Cred-shaped non-creds: KYC/fraud threads carry national-ID formats next to password labels (e.g. 18-char Mexican CURP `RASF840517HCLMTL06`) — classify before spraying.
- A readable lower-env instance leaks prod username formats — pull the user table from preprod/stage and replay alias conventions (`name.x+admin@domain`, `+staff@`) on prod, 1 attempt per pair.
- Editing the sweep script between waves: patch the TERMS array properly (not `sed` on a multi-line literal) and `python3 -m py_compile` before launching the next long background run.

## Files

- `references/shortcut-clubhouse.md` — Shortcut private-API endpoints/headers, CDP eval pattern, entity shape, resumable sweep design.
- `references/corpus-lead-expansion.md` — command patterns for GitHub-org / Google-Docs / OneTimeSecret / attachment / GitBook / OpenAPI lead expansion.
- `scripts/cred_scan.py` — standalone credential-regex scanner over a fetched corpus.
