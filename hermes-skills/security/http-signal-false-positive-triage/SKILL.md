---
name: http-signal-false-positive-triage
description: Triage ambiguous 200/403/proxy/file signals.
version: 1.0.0
---

# HTTP Signal False-Positive Triage

**Use before calling any HTTP/proxy/recon result a finding.** A status code alone
is not evidence. Every positive needs a control comparison and, where possible,
a state read-back.

## 0. Evidence packet

For each candidate record: URL, method, status, `Content-Type`, body length,
SHA-256 of the first 4 KB, and the read-back state. An "exploit" without a
read-back is only an observation.

```bash
curl -sS -m 10 -o /tmp/probe.body \
  -w '%{http_code} %{size_download} %{content_type}\n' \
  'https://TARGET/path'
sha256sum /tmp/probe.body
```

## 0b. Scheme first: HTTP 400/000 is not a dead port

Non-standard ports are often HTTPS-only. Probe both schemes before declaring
the port dead:

```bash
curl -k -sS -m 8 -o /tmp/h -w 'https %{http_code} %{size_download}\n' "https://HOST:PORT/"
curl    -sS -m 8 -o /tmp/h -w 'http  %{http_code} %{size_download}\n' "http://HOST:PORT/"
```

- HTTP `400`/`000` + HTTPS `200` -> HTTPS-only, not dead.
- A `:80` 301 to `https://HOST:4455/` gives the real scheme/port in `Location`.
- `000` is curl connection failure, not an HTTP status; through SOCKS separate
  proxy failure from target refusal.

## 1. API "success" that is a catch-all mock

Symptom: many unrelated endpoints return the same tiny body, e.g. an 82-byte
`{"code":0,"msg":"操作成功"}`.

Control steps:
1. Request a deliberately nonexistent sibling, e.g. `/api/user/__no_such_route__`.
2. Compare body length, body hash, `Content-Type` with every candidate.
3. Read back the protected field from a known real endpoint (`/me`, `getUserInfo`).
4. If the nonexistent route and all candidates match, and `isAdmin`/`role` is
   unchanged, call it **catch-all mock**, not mass assignment, not L1.

A 200 response is not L1. L1 requires the field value to change on read-back.

## 2. Vite `?raw` and SPA fallback

- A 200 with `Content-Type: text/html` for `.env`/`.git/config` is usually the
  SPA index fallback, not a file read.
- Confirm a real read by expected structure: `package.json?raw` must parse as
  JSON, `vite.config.ts?raw` must contain TypeScript; `/@fs/etc/passwd` should be
  403 when `fs.deny` works.
- Fingerprint the exact Vite version from `package.json`/`package-lock.json`
  before hunting a version-specific bypass. Vite 6.4.3 already contains the
  2025-2026 `fs` bypass fixes; do not keep throwing old `?raw??` payloads.

### 2b. Project-root files are a real leak, not a fallback

`/package.json` or `/vite.config.js` returning 200 is not automatically a Vite
fallback. Parse before deciding:

- `package.json` must `json.loads` and contain `"name"` / `"dependencies"`.
- `vite.config.js` must contain `defineConfig` and preferably `server.proxy`.
- `Content-Type: text/html` plus body starting `<!DOCTYPE` = SPA fallback, not leak.
- `/src/*` returning 404 does **not** disprove a project-root leak; Vite serves
  root config files as static assets independently of the dev source tree.

A real `vite.config.js` gives `server.proxy.target` (backend host) but that host
may have dead DNS. Treat it as a lead, not as a live backend.

## 3. Free-proxy egress: control URL or it did not happen

Every candidate proxy gets the same request to a neutral control
`http://example.com/` and to the target.

| Control | Target | Conclusion |
|---|---|---|
| 403 / block page / timeout | same 403 / block / timeout | proxy-side ACL/device; discard proxy |
| 200 | 403 / different body | target-specific response; proxy usable |
| 200 | 200 same body | proxy is a device self-answer page; inspect first 600 chars |

Never report "reached the target" from a proxy hit when the control also fails.

## 4. WebSocket 403 on every path/origin

If 9 paths x 6 Origin values all return 403 and none returns `101 Switching
Protocols`, the edge/server is blocking the Upgrade itself. That is not proof of
Origin validation and not proof of CSWSH. Stop the Origin matrix and pivot to
HTTP routes or the frontend bundle.

### 4b. Time-based SLEEP through a proxy: one delta is not evidence

Symptom: `id=1 AND SLEEP(3)` returns 4.58s against a 2.0s baseline — looks like
SQL injection. A retest returned 2.07s against 1.53s; the first sample was SOCKS
jitter, not injection.

Rule for any timing oracle through a proxy/Tor/SOCKS chain:

1. Baseline: 3 requests, same method/path/headers, no payload.
2. Test: same payload 3 times, not once.
3. Control: same-shape parameter with `SLEEP(0)` or a random string; confirm it
   does not add delay.
4. Require a **consistent** delta larger than normal jitter, with matching
   status and body; otherwise write “不确定”, not “SQLi”.

A single slow response is an observation, never a finding.

### 4c. A new IP serving the same API is a mirror, not a new backend

Before treating a newly discovered IP as a new data plane, compare identity:

- Same token works on both IPs.
- Same user object / same business row returns.
- Same fatal-error path (`/www/wwwroot/.../file.php:line`) returns.
- Same config body length/hash.

All four equal → **same DB/source mirror**. Record it as an alias, do not re-dump,
and do not count it as a new attack surface. Different IP + same token is not a
new privilege boundary.

## 5. Certificate names are not live assets

`crt.sh`/CT names are historical. Resolve A/AAAA and TCP-connect before calling
one a host. Zero open ports after a real scan = dead certificate record, not a
hidden service and not a scanning failure.

## 6. Cloudflare 526 + port 80 redirect

`526` on 443 plus a 301 from 80 to https means Cloudflare cannot validate the
origin certificate. It does not expose a second origin. Do not keep guessing
`api.`/`cpanel.` hosts on the same Cloudflare edge.

### 6b. 403 body first: ICP block vs WAF vs vhost

Before running a Host/XFF matrix, read the 403 body:

- ~640-byte page containing `ICP`, `备案`, or `Non-compliance ICP Filing` →
  Aliyun/edge **ICP filing block** for that domain/port. It is not a vhost, not a
  WAF rule, and not evidence of an IP allowlist. Stop the Host matrix.
- `站点创建成功` / default nginx page → default vhost, not the app.
- `Access denied.` (very short) → PHP-FPM `security.limit_extensions`, not app auth.
- Real WAF challenge page → then and only then try header/encoding bypasses.

## Stopping rules

- Same body/hash as a nonexistent route -> stop, write negative.
- Proxy control also blocked -> stop that proxy, do not retry payloads.
- All WS paths/origins 403 -> stop Origin enumeration.
- Cert name resolves but zero ports -> mark dead, move on.
- Vite version is patched -> stop version-CVE guessing; only test a new
  vulnerability with a version-specific proof.

## Session evidence

- `references/2026-10-hutaocards.md` — exact control results (mock API, Vite fallback, proxy block, WS 403, dead CT records) from the case that produced this card.
- `references/2026-10-socks-jitter-icp-mirror.md` — SOCKS-jitter SLEEP false positive, Aliyun ICP 403 body, new-IP mirror check, Vite root leak vs fallback.

## Related

- SPA 工程根/JS chunk → 后端端点恢复 → `spa-source-leak-endpoint-mining`

## Reporting language

Use "判死/不成立" with the control result, not "可能/疑似". Save the exact
status, length and hash so a later round can compare without re-running blind.
