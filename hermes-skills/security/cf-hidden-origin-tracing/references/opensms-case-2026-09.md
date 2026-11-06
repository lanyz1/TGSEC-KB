# Case: opensms (CF Pages + Worker front for a CN SMS panel), 2026-09

Worked example behind the techniques in SKILL.md. Credentials redacted.

## Target shape
- `https://www.opensms.xin` -> 301 -> `https://www.opensms.cc` (Turnstile on `/login`).
- Front end: **CF Pages**; `/csapi/*` is reverse-proxied by a **CF Worker** to the real API.
  The bundle even carried a developer note: "Worker ORIGIN must point at the real API, not the
  Pages domain" — i.e. the origin is deliberately never exposed to DNS.
- A second panel of the same operator: `proxy.opensms.cc` (management console, RuoYi-Vue, its own
  Turnstile sitekey). Both hostnames resolve to the same CF IP set.

## Client protocol (mined, then reimplemented — and it still failed)
- `POST /csapi/crypto/handshake` with header `CF-Turnstile-Token: <tok>`, body `{"clientPubKey": "<b64 65-byte P-256>"}`
  -> `{sessionId, serverPubKey}` + `Set-Cookie: __hs=...` (Max-Age 300).
- Key: P-256 ECDH -> HKDF(info=\`sms-im-ecdh-session-v1\` + 0x01) -> AES-256-CBC.
- Business calls: `Content-Type: text/plain`, header `X-Session-Id`, encrypted body;
  response body encrypted when `X-Encrypted: true`.
- Login plaintext (captured with a main-world `JSON.stringify` hook):
  `{"username":"...","password":"...","theme":"default"}`.
- `__hs = base64("hs|<clientIP>|<ts>:<HMAC>")` -> session bound to client IP.

**Result: a byte-identical replica (headers, cookie, session id, payload, egress IP, even a second
handshake on the same cookie, with 0-3 s gaps) still returned the panel's `4011 session expired`,
while the same browser's own SPA login returned a real auth response. TLS/HTTP2 profile or an in-page
keepalive superseding the session are the remaining suspects. Conclusion recorded: drive the real UI
for main-panel authenticated calls.**

Egress-IP innocence was proven separately: `/cdn-cgi/trace` through the pinned exit said
`ip=45.84.107.200`, and the freshly issued `__hs` decoded to exactly `hs|45.84.107.200|...`.

## Gateway leak channel (worth checking on every such target)
`access-control-expose-headers: X-Whitelist-Block, X-Turnstile-Block, X-RateLimit-Block,
X-Handshake-Block, X-Origin-Block`. Confirmed: nonsense path -> `x-path-block: 1`;
`/csapi/vim/server/config` before login -> `x-whitelist-block: 1` + `{"code":403,"msg":"请先登录"}`.

## The historical-IP generation, and why it is dead
- ip138 history for `opensms.cc`: 2026-06-20 -> `47.91.170.222` / `47.76.127.217` / `8.218.208.240`
  (Alibaba Cloud HK); 2025-12-21 -> `18.185.24.46` (AWS Frankfurt); earlier -> CF.
- `whois opensms.cc`: **Creation Date 2026-09-15**, Updated minutes later, different registrant/NS
  from the previous round => the June infrastructure belongs to a previous generation.
- The three Alibaba IPs: no response from outside (that alone is not proof — CF-only allowlists are
  the normal case), so they were probed **from inside Cloudflare** via a CF-Worker-hosted fetcher
  with a live control IP in the same batch: control `200`, all three `statusCode: null`.
  **That "dead, not firewalled" verdict was later withdrawn as invalid.** The probe fetched
  `https://<ip>/`, i.e. **SNI = the bare IP**, and the control IP happened not to need a matching
  vhost — so the asymmetric `null` may be a TLS/host rejection, not death. A CF-only allowlist is
  invisible to every vantage we own (own box, `/24` sweep, IP-URL fetch). Correct status: **proof of
  death NOT established; these remain the leading origin candidates**, to be settled by a fetcher that
  controls `Host:` (plain `http://<ip>/` + `h=`, or a Worker with a Host override) — SKILL.md §3, §10.
  Full `/24` sweeps plus `Host:`-header fingerprinting from outside found nothing, which is expected
  if the origin only answers CF sources.
  **Lesson recorded in the skill: never let an IP-URL `null` stand as proof of death.**

### Settled in the next round: those three IPs are Cloudflare itself
The cross-host test closed it. Requesting **`example.com`** through `47.91.170.222` / `47.76.127.217` /
`8.218.208.240` returned **Example Domain**, and their TLS cert was a public-CA cert covering
`www.opensms.cc` (Google Trust Services **WE1** = Universal SSL). => the 2026-06-20 Alibaba-HK
"origin candidates" are **CF anycast edge IPs** (CF announces from Alibaba-HK space); the operator's
origin was never exposed in DNS. Status upgraded from "unproven" to **not publicly reachable, by
construction** — consistent with the bundle's own 「源站超时，请稍后重试」 copy (proxy -> origin).
Also run, and ruled out: full `/16`s `47.76.0.0/16` + `47.91.0.0/16` (262,136 targets / 34,677 open
hosts) fingerprinted from inside CF with CF edges excluded => zero panel hits; `58.67.156.43`
(Host `proxy.opensms.cc`, title 「广州首易信息技术有限公司-企业短信系统Web版」) is an anti-DDoS WAF
(`server: ADM/2.1.1`), not an origin; `18.185.24.46` is the operator's own `redirectv2` Go redirect
service, alive on :80/:443.
Probe-hygiene note: an entire batch of "dead" readings was discarded because the control listener sat
behind `ufw` (default `INPUT DROP`) and was unreachable from the CF edge — see SKILL.md §3.

### The in-app path did pay (this is where the value was)
In-session credential spraying against the main panel (see `password-spray-lockout-bypass`) landed a
working account; with its `sa-token` the panel answered `GET /vim/server/config` 200,
`/vim/server/notices` 200, `/vim/server/users/my` 200, `/vim/server/chat/list` 200 (business objects
carrying card/device ids), `/csapi/wsOnline` 200. The operators' own notice text: **「我们3个机房有一个
机房因为漏水（30%卡量）需要搬迁」** — three physical SIM-farm sites and their card inventory, i.e. exactly
the asset the source-IP hunt was a proxy for. Verb notes: `PUT` for `/vim/server/setting`;
`users/list` and `groups/list` answer `{"code":500,"msg":"服务器繁忙，请稍后重试"}` (500 = route
exists, retry with pagination/params).
- CT: `single.opensms.xin`'s certificate was issued by **TrustAsia (Chinese CA)** => that hostname was
  once served straight from a CN/HK box; it is `NXDOMAIN` today (migration debris).
- Shodan by favicon mmh3 / cert / hostname / HTML body: all zero. urlscan API: 403 unauthenticated.

## Where the trail actually leads
In-app config endpoints that would name the origin (all `403` at agent privilege, need an admin
account): `/api/monitor/server`, `/api/system/config/list`, `/api/phone/config/list`, `/api/system/user/list`.
Meanwhile the agent-level console token **is** scriptable from Python (bearer `Admin-Token`, not a
session cookie) — the two panels are registered in separate user stores, and only this one is
reachable from scripts. Getting a higher-privileged account was handed to
`password-spray-lockout-bypass` (case-variant lock bypass, see that skill / its case reference).

## Verdict delivered to the user
Origin IP is **not externally obtainable with the vantages we hold**, and the single remaining path is
in-app configuration under an admin account — plus a self-deployed CF Worker as an egress probe.

## Cloudflare-account handover attempt (instructive failure)
The user supplied a CF **Account ID** (`21aa09e3f5fac38be39acf699af2cc00`), an **API token**, and an
**R2 S3 key pair + endpoint**. Verdict after checking, before promising anything:
- token = <REDACTED>, **R2 scope only**, and carrying **`not_before: 2026-09-17T00:00:00Z`** — inert for
  another ~3h49m at hand-over, and scoped away from Workers even after that (`/user/tokens/verify`
  parses fine; `/accounts/<id>/workers/scripts`, zones and members all return `Authentication error`).
- R2 S3 credentials cannot deploy a Worker or read zone config — they unblock nothing here.
=> Answered with the exact token recipe to request next time (Custom Token, Account -> Workers
Scripts -> Edit, TTL/Start date EMPTY) and with the alternative of pasting the Worker into the
dashboard themselves and returning the `*.workers.dev` URL. Checklist lives in SKILL.md §10.

Also fixed in this round: the "`x-origin-block` gate" was a **grep false positive** (it only matched
inside the `access-control-expose-headers` value); the real gate vocabulary is `人机校验未通过` /
`请先登录` / `Bad request`, and `x-path-block` fires on `/csapi/%2e%2e/...` paths (normalised to the
SPA shell, or back into the `/csapi/` prefix where `x-whitelist-block` then applies).
