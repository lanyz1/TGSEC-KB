# SOCKS jitter, ICP 403, and new-IP mirrors (2026-10)

Session evidence and reusable control tests. No credentials, tokens, or PII.

## 1. Time-based SLEEP false positive

Target endpoint accepted `type`; first test:

```
type=2 AND SLEEP(3)  -> 4.58s   (baseline ~2.0s)  => looked injectable
```

Retest, same request, alternating baseline and payload:

```
baseline             -> 2.07s
payload              -> 1.53s baseline / 2.07s payload
stacked/multi-form   -> no consistent difference
```

Conclusion: the 4.58s sample was SOCKS proxy jitter, not SQL injection. The
finding was explicitly retracted; no write payloads were sent.

Reusable rule:

- 3 baselines + 3 payloads + 1 same-shape control (`SLEEP(0)` / random value).
- Require a repeatable delta, not one spike.
- Through SOCKS/Tor, treat any delta under ~2x normal jitter as inconclusive.

## 2. Aliyun ICP 403 is not a vhost

`GET http://HOST:14845/` with `Host: test...`, `Host: h5...`, `Host: img...` all
returned **403, 640 bytes**; no Host returned 404. The 640-byte body was the
Aliyun **ICP filing block page** (`ICP` / `Non-compliance ICP Filing`), not an
application auth page and not a vhost route.

Control interpretation:

- 403 + 640B + ICP text → domain/port edge block; Host matrix is useless.
- 404 without Host → no default app route either.
- Do not report “vhost exists but IP allowlisted” from this pattern.

Other short-body 403s:

- `Access denied.` (~15B) → PHP-FPM `security.limit_extensions`.
- `站点创建成功` → Baota/default vhost page, not the app.

## 3. New IP mirror check

A newly found IP served the same `php_api` path. Identity checks:

- same root token accepted on both IPs;
- same user object returned by `user.php`;
- same 3,006-byte `index.php` body;
- same fatal error path `.../test.guokuzhongxin.com2/php_api/inv_record.php:151`.

Conclusion: **same DB / same source, new ingress only**. No new data, no new
privilege. Do not re-dump or count it as a separate asset.

## 4. Vite project-root leak vs SPA fallback

On the same new IP:

- `GET /package.json` → 200, real JSON, `name="card"`, Vue3/Vite8/vue-router5/axios.
- `GET /vite.config.js` → 200, 2,508 bytes, `defineConfig`, proxy target a
dead domain.
- `GET /src/*` → all 404.

So: project-root files can be exposed while the dev source tree is not. Parse
`package.json` as JSON and `vite.config.js` for `defineConfig`; do not call a
200 an SPA fallback without checking the body. The proxy target is only a lead
because its DNS may already be withdrawn.

## 5. Asset-discovery rate limits

FOFA returned `45012` (rate limit) and crt.sh returned 429/502 during the same
window. That is “retry later / change source”, not “no assets exist”. Save the
error code and do not write a negative finding from a rate-limited query.
