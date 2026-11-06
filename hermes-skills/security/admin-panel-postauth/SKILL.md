---
name: admin-panel-postauth
description: "Use when you have web admin access: triage, upgrade, clean."
version: 1.0.0
tags: [pentest, admin, post-auth, laravel, upload, cleanup]
---

# Admin Panel Post-Auth

Use after a login bypass, credential reuse, or leaked session gives you a Web admin panel. The question is no longer “can I log in” — it is **how real is this panel, what can it write, can it be upgraded to RCE/DB/another tenant, and how do I leave no test data behind**. A panel that returns a 200 dashboard is not automatically a win; a panel with a real user list, writable settings, and CSRF-protected forms is.

## 0. Classify: real admin vs dashboard shell

| Signal | Real admin | Shell / half-built / honeypot |
|---|---|---|
| `/admin` title | business name (“仪表盘 - X Telecom”) | generic dashboard / blank |
| Side menu | orders, products, users, coupons, payment, shipping, notifications | a few items; every item opens the same shell |
| Lists | real rows, pagination, working search | empty/fake tables, fixed 2–3 KB HTML |
| Forms | CSRF field (`_token`), POST returns business error or 302 | all POST/PUT return 405 |
| Upload | multipart action, real stored path | fixed mock path such as `products/up.jpg` |

If every write is 405 and every sub-page is the same 2–3 KB dashboard shell, stop treating it as a compromise: record it as a **read-only/mock panel** and pivot. Do not spend rounds trying to “unlock” a deliberately fake panel.

## 1. Inventory before exploitation

For every menu page: fetch it, save the HTML locally, and record route, row count, column names, form actions, CSRF field name, and HTTP method. Do not paste PII into chat; report counts and field names only.

Priority order:

1. Users / orders / products / coupons — count and field names.
2. Settings: payment, SMTP, notifications, packing-slip/footer, shipping.
3. Upload / import / export endpoints.
4. Anything that renders a PDF, invoice, label, or template.

## 2. Highest-yield move: sibling-app credential reuse

One operator usually runs several apps with the **same admin email/password**, but the apps are not equally complete. A mock/read-only panel on app A may share credentials with a full commerce panel on app B. After any admin credential is recovered:

1. Collect sibling subdomains from CT logs, `api.certspotter.com`, and FOFA `cert="<domain>"`; also try `--resolve` against known origin IPs.
2. For each sibling, request `/admin` and `/login`; fingerprint title, framework, session-cookie name.
3. Try the same email + password **once per app** (hard cap: 3 apps / 3 attempts; stop on lockout).
4. On a hit, immediately fetch `/admin` and its menu pages; classify real vs shell using §0 before investing further.

This is a credential-reuse pivot, not password spraying: one known-good pair, a small sibling list, no dictionary.

## 3. Upgrade matrix (test in this order)

### 3.1 File upload → webshell / path control

Two separate tests, one round only:

- **Extension test**: valid JPEG bytes + `.php` filename. If rejected/302 back to create, the control is an extension whitelist, not MIME.
- **Content test**: valid `.jpg` extension + JPEG/PHP polyglot. Retrieve the stored file and inspect bytes. If the server stores a hashed `.jpg` and serves it as an image, PHP in the body is inert.
- Try `.phtml`, `.phar`, `.htaccess`, `.user.ini`, `.php.jpg`, `.phar.jpg` once each; record status. Then test path-info: `/uploads/x.jpg/x.php`, `%00`, `;.php`, `%2f..%2fx.php`. A 404/403 matrix is a **dead end**, not a reason to keep fuzzing.

### 3.2 PDF / template / invoice rendering

Do not start with `/etc/passwd`; first prove whether the renderer interprets HTML at all:

1. Put `<b>MARK</b>` in footer, product name, or recipient name.
2. Export the PDF and run `pdftotext`.
3. If the output contains literal `<b>MARK</b>`, the field is HTML-escaped; mPDF/Blade injection is dead — stop.
4. Only if the marker is interpreted, try `<annotation file="/etc/passwd">`, then `pdfdetach -list` and `strings` for `root:`.

A PDF with 0 attachments and literal tags is a **negative result**; do not keep changing path payloads.

### 3.3 SQL injection in admin search/filter

Test the search and filter parameters (`q`, `status`, `type`, `role`) with a single time-based probe. A custom 500 page, a redirect, or a generic error is not proof. If the app uses an ORM/query builder and the probe shows no delay, record “no time-based SQLi” and move on.

### 3.4 Settings → SSRF / file write / credential capture

Look for settings that accept a URL, host, path, UNC, webhook, or certificate location. If the form actually saves and has a “test” action:

- Point SMTP/HTTP/webhook fields at a listener you control; confirm the callback.
- Point a certificate path at a UNC path to capture NTLM, or at `http://169.254.169.254/...` for cloud metadata — only if the app performs a real fetch, not just stores the string.
- Verify by reading the setting back and observing the listener; a saved string alone is not SSRF.

### 3.4b Test-connection / health-check endpoints

Admin panels often expose a "test connection" action for SMTP, S3, RTC or webhooks. It is
a higher-yield SSRF than a generic URL field because the operator expects a server-side
request. Point the URL at a listener you control and confirm the callback. If the response
returns only `{"status":"connected"}` while the callback is real, this is **blind SSRF**,
not full-read SSRF; operation logs commonly store only status, not the fetched body. Look
for a second test endpoint that echoes the response body before claiming a read primitive.

### 3.5 Import / export / queue / logs

- `/import` that is POST-only, 405, or has no form is not an entry point.
- Export CSV/PDF may leak PII; use headers/row counts, do not dump into chat.
- Queue/log viewers are high-value; check menu and common routes, but do not brute-force dozens of paths.

### 3.5b Admin API export: pull the declared totals first

A real `super_admin` panel is an export surface even when the UI hides the export button. Fetch
the dashboard/statistics first and record `total` for users, wallets, groups and channels;
then paginate each list with the API's own `page`/`pageSize`, write CSV + JSON locally, and
compare the last page's row count with the declared total. In one SaaS case this produced
3,971 users, 3,536 wallets and 118 groups from four read-only list endpoints. Keep PII local
and report only counts/field names.

Do the export **before** touching any write endpoint: tokens expire, and a read-only dump is
the durable evidence. Do not call wallet mutations, approvals, broadcasts or settings writes
just because the role permits them; state the boundary in the report.

### 3.6 Business logic

If the panel can create a **100% coupon** or set a product price to zero, a ¥0 order is a valid minimal PoC for a pricing/coupon weakness. Keep it minimal:

- fixed-amount or 100% coupon, no real payment;
- one or two orders maximum;
- download the invoice/PDF if needed;
- cancel the orders during cleanup.

Do not call this an unauthenticated vulnerability: it is an **admin-configurable business-logic risk** unless the coupon can be obtained/used by a normal user.

### 3.7 Ask the panel about itself FIRST: introspection endpoints are credential oracles

Before spending a round on upload/PDF/SQLi/RCE, hit the panel's **self-reporting endpoints**. Many stacks expose the running process's own config, and that hands you every downstream password in one request:

| Stack | Endpoint | What it returns |
|---|---|---|
| RuoYi / 若依 | `GET /monitor/server` | `jvm.inputArgs` = `-DMYSQL_PASSWORD` / `-DREDIS_PASSWORD` / `-DACCESS_KEY` **in plaintext**, plus `sys.userDir` (deploy path) and JVM home (panel type) |
| RuoYi / 若依 | `GET /getInfo` | `user.twoFactoryCode` = **TOTP secret in plaintext**; `password` bcrypt |
| RuoYi / 若依 | `GET /monitor/cache/getNames` → `getKeys/{n}` → `getValue/{n}/{k}` | reads the app's **Redis** contents: `login_tokens:*`, `sys_config:*` (incl. default password) |
| Spring Boot | `/actuator/env`, `/actuator/heapdump` | property sources / heap (only if exposed) |
| Laravel | `/telescope`, `/.env` via debug page | env secrets |
| Django / Flask | debug traceback, `/admin/` status pages | `SECRET_KEY`, DB URL fragment |

Rules:

1. Harvest **before** attempting RCE — it is one GET, no lockout, no side effects.
2. Verify each secret actually works (Redis `AUTH`, DB connect) and label it: **verified-usable** vs **obtained-but-unreachable**. A correct MySQL password against a localhost-bound MySQL is still `1045` from outside — report it as intelligence, never as “database access”.
3. Default-password values found in app config (`sys.user.initPassword`) feed the credential-reuse step in §2.
4. Login/operation log endpoints (`/monitor/logininfor/list`, `/monitor/operlog/list`) are operator profiling gold: login-IP frequency and real business-action distribution.

### 3.8 Auth-bypass API → ship a single-file browser console, not a curl snippet

When the gate is a broken interceptor rather than a credential — e.g. it only checks that
`Authorization` starts with `Bearer ` and never validates the value — the operator's real
question becomes "how do I use this". Answer with an artifact.

1. **Confirm the bypass per method family.** One GET, one POST, one PUT with a junk value.
   Record the exact header that passes. A 200 on `/list` only proves that route.
2. **Check CORS before promising a browser panel.** Send `Origin: http://localhost` plus an
   `OPTIONS` preflight with `Access-Control-Request-Headers: authorization`. You need BOTH
   `Access-Control-Allow-Origin: *` (or a reflected origin) AND `authorization` listed in
   `Access-Control-Allow-Headers`. With both, a plain `file://` HTML page can drive the API
   directly. Without both, generate a CLI client instead — a browser page will be blocked and
   you will look like you shipped something broken.
3. **Generate the console from the spec.** Parse `/v2/api-docs` or `/openapi.json` into a
   compact `[{method, path, tag, summary, params[]}]` table and embed it in one HTML file with
   a single generic `send()` that routes `in:query` into the query string and
   `in:body`/`formData` into a JSON body. Every endpoint then works for free, with no per-route
   hand-coding, and the artifact stays correct when the target adds routes.
4. **Prefill required params** on both preset rows and on render (`page=1`, `limit=20`). An
   empty required param returns a 400 that reads as "the panel is broken" when it is your
   template that is wrong.
5. **Click through it in a real browser before delivering.** Open the file, hit two different
   presets, read the rendered response, and quote status / latency / bytes / `total`. A panel
   you never exercised is a guess, and the operator will discover that immediately.
6. **Report the artifact plus the bypass header.** The header IS the credential — say that
   plainly instead of implying you recovered a password. Also state the CORS finding as its
   own weakness: it means anyone who learns the API host can drive it from any web page.

While you are in the spec anyway, sweep the config/settings endpoint field-by-field for
third-party keys (`ipdatacloud`, SMS, map, captcha, OSS). They are routinely stored plaintext
next to cosmetic settings and are independent intelligence even when the panel itself is the
finding.

## 4. Cleanup: 302 is not deletion

Test data is part of the engagement. A delete request returning 302/200 only means the route accepted the request; it does **not** prove the row is gone.

1. Locate every test object by a unique marker (`R22FREE`, `R22CODE`, test email).
2. Parse the **form action on that specific row**; do not guess `/admin/<resource>/1`. Different resources have different routes (e.g. `/admin/virtual-items/{id}`).
3. Delete, then re-fetch the list and search for the marker; require 0 hits.
4. Orders usually have no delete route: set status `cancelled`, record the order IDs.
5. Restore any setting you changed (footer, description, payment, mail). Save original values **before** the first write; if you did not, report “not restored — original not captured”. Never fabricate a restore.
6. Test accounts may have no delete route; product deletion may leave uploaded files in storage. Delete what you can, and list the residual account/files in the report.
7. Before deleting, print row ID + unique marker + creation time. If the ID does not match the marker, stop and re-parse — a first cleanup pass can delete the wrong IDs while the test rows remain.

## 5. Reporting

Separate **currently held** from **previously held / expired**. State plainly:

- panel type and evidence (title, menu, row counts);
- what is writable, with one minimal PoC;
- what was tried and failed (upload, PDF, SQLi, import, settings, SSH/DB), with the decisive signal;
- what test data was cleaned, what could not be restored, and exact residual identifiers;
- what was NOT obtained (root/DB/shell) — do not dress an admin panel up as root.

## Pitfalls

- A 200 dashboard is not a compromise; a real user list and a working write form are.
- Do not spray the sibling list. One known email/password, ≤3 apps, one attempt each; lockout destroys the pivot.
- Do not test `.php` upload with a PHP body first; it conflates content filtering with extension filtering. Use valid image bytes + malicious name.
- Do not start PDF injection with `/etc/passwd`; prove HTML interpretation with `<b>MARK</b>` first.
- A 405 on `/_ignition/execute-solution` means the route exists, not that Ignition is exploitable.
- A 302 after delete is not proof; re-fetch. Absolute vs relative form actions can also break your URL construction.
- Do not “clean” by editing the database directly; use the panel, and record what remains.
- **Extension preserved is not execution.** An upload endpoint that keeps `.php` and returns a public URL is still static if retrieval is `application/octet-stream`. Request the URL with and without a query parameter; only a parsed/executed response upgrades it to RCE.
- **A real callback with `{"status":"connected"}` is blind SSRF, not full-read.** Confirm the server-side request first, then look for an endpoint that returns the fetched body. Do not overstate it in the report.
- **Export before you write.** A `super_admin` token is time-limited; dump the read-only user/wallet/group lists first, verify counts against the dashboard total, and only then consider a minimal write PoC.
- **Ask the panel about itself before hunting RCE.** `/monitor/server`, `/actuator/env`, `/getInfo`, debug/status pages routinely return process start args, env vars and TOTP secrets in plaintext — one GET can beat a whole RCE chain. Harvest, then try the credentials; if the DB is localhost-bound the password is still reportable intelligence, not a shell.
- **A bcrypt-verified password reset on a tenant row does not prove the login endpoint reads
  that table.** If `/admin/login` still answers "wrong password" after you reset an account to
  a password you hold and verified the new hash locally, the admin credentials live in a
  **separate table** from the tenant/enterprise accounts. That is the conclusion — do not
  burn a matrix of encodings (plain / md5 / sha1 / sha256 / base64 / the account key) hoping
  one lands. A generic "wrong password" for both existing and non-existent accounts also
  means there is no enumeration oracle, so stop probing for one.
- **`b'"code":200' in body` matches `"code":2003`.** Substring matching on JSON status codes
  produces false HITs and will have you celebrating a failed login. Match a full token
  (`"code":200,`), or better, `"success":true`, or parse the JSON and compare the integer.
  This bug is silent — it only shows up when a code happens to share a prefix.
- **Some ports exist purely to answer you.** A fixed 2-byte body (`NO`) on an unusual port,
  identical across hosts, is an anti-recon decoy, not a service. Do not fold it into the
  attack surface or spend rounds fingerprinting it.
- **Deliver the usable artifact, not the finding.** For an API bypass the operator wants an
  entry point they can click. A browser console generated from the spec (see §3.8), verified
  by two real requests, beats a report paragraph describing the same bypass.

## Verification checklist

- [ ] Panel classified as real vs shell with evidence
- [ ] Menu/list/form/CSRF inventory saved (counts, no PII in chat)
- [ ] Sibling apps checked with ≤3 credential-reuse attempts
- [ ] Upload tested in two passes; path-info tested once
- [ ] PDF/template tested with a harmless marker before file paths
- [ ] SQLi search/filter tested once; 500 not treated as proof
- [ ] Settings tested for real fetch/callback, not just string storage
- [ ] ¥0/business-logic PoC minimal, no real payment
- [ ] Test rows deleted and verified by re-fetch; orders cancelled
- [ ] Settings restored or residual honestly reported
- [ ] Report separates held vs expired and admin vs root/DB/shell

## References

- `references/laravel-admin-case-notes.md` — concrete Laravel 8 admin case: routes, two-pass upload results, escaped mPDF marker, 0-yuan orders, cleanup residue and the 302-not-deleted trap.
- RuoYi-specific credential-oracle transcript (exact endpoints, response shapes, credential usability matrix, hardened-build dead faces): see `ruoyi-framework-pentest` → `references/monitor-server-credential-oracle.md`.
- For the wildcard-vhost → Vite admin SPA discovery chain and the full SaaS takeover/export case, see `white-label-platform-recon` §2l and its `references/wildcard-admin-spa-and-post-auth-chain.md`.
- `references/auth-bypass-api-console.md` — full worked case: prefix-only `Bearer` interceptor, permissive CORS check, spec-driven single-file console (generator + JS `send()` shape), the two-table login diagnostic, and the substring-match false-HIT bug.
