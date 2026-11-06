# cast-sec worked example (2026-09)

Commercial bot wall seen on a scam-casino origin behind Cloudflare. Everything
below is measured, not inferred.

## Response fingerprint

```
HTTP/2 666
cache-control: no-store, no-cache, must-revalidate, max-age=0
cast-mode: default
server: cast-sec
set-cookie: cs-uuid=<32 hex>;path=/;max-age=3600
set-cookie: cs-resp=;path=/;max-age=0
via: 1.1 Caddy
```

Body: 5,103 bytes, obfuscator.io — `var a=['c8Knw6cvLw3DmxDDmQ==', ...]` plus
`var b=function(c,d){...}`.

## Decoded challenge (via the script's own `b(idx,key)`)

```js
window.onload = function() {
  var k = document.createElement("script");
  k.type = "text/javascript";
  k.src  = "/verifyjs";
  document.getElementsByTagName("body")[0].appendChild(k);
};
```

Other decoded strings: `getElementById`, `createElement`, `appendChild`,
`submit`, `onload`, `body`, `src`, `type`, `text/javascript`.

`GET /verifyjs` (with only `cs-uuid`) returned:
`<html><meta http-equiv="refresh" content="0; url=http://noawin.com/"></html>`
→ loop back to `/` → challenge again. So the vendor expects a real browser
fingerprint; exit rotation is cheaper than solving it.

## What failed (do not repeat)

- **Reimplementing the RC4 decode in Python.** base64 → latin-1 → RC4 produced
garbage for all 36 call sites. Root cause: JS `charCodeAt` operates on UTF-16 code
units, the Python port on bytes. Fix = execute their function in Node.
  Reimplementations of this class of decoder are a trap; drive the original.
- **UA whitelists:** Googlebot, bingbot, facebookexternalhit, Twitterbot, curl,
  python-requests, iPhone Safari, PostmanRuntime, okhttp → **all `666`**.
- **Header spoofs** (X-Forwarded-For / X-Real-IP / True-Client-IP / X-Client-IP):
  ignored on the CF-fronted side; `CF-Connecting-IP` → Cloudflare `error code: 1000`.
- Crawler UA + `Accept-Language` + `Accept: */*` combinations: no change.

## What worked — exit row only

| Request | Exit | Result |
|---|---|---|
| `https://target/robots.txt` | local datacenter egress | `666` + challenge |
| same, via Tor (`--proxy-user` random) | Tor exits | `403` (nginx-style 403, cast-sec's other branch) |
| same, via Tor, `--resolve target:443:<origin>` | Tor exit | **`200` + real site** |
| `GET /favicon.ico` | local egress | **`200` (not walled)** |
| `GET /.well-known/security.txt` | local egress | `403` (third code, per-path rule) |

Takeaway: the same host answered with three different status codes depending on
path and exit — the code is a diagnostic instrument, and per-path rules exist.

## Origin identification

- Candidate IP from OSINT (`hostsearch` on a sibling brand) → `66.198.225.39`.
- `nmap -sV` → `22 OpenSSH 8.9p1 Ubuntu`, `80 Caddy httpd`, `443 ssl/https`.
- `whois 66.198.225.39` → `SKN Subnet & Telecom Ltd`, country **KN** — i.e. **not
  Cloudflare**, even though every API response carried `server: cloudflare`.
  That header is forged by the application; whois is authoritative.
- `Host: <victim-brand>` on that IP returned the brand's **full 250 KB site**
  (`200`), while sibling brands on the same box returned `666` / `403` — one
  shared origin serving many brands.
- Direct (non-Tor) egress to the origin failed outright while Tor succeeded →
  origin-level IP allowlist.
- 25 rapid registrations through the origin: 14 reached application logic → no
  edge rate limiting in the path, i.e. Cloudflare genuinely bypassed.

## SOCKS5 port scan through Tor (no proxychains installed)

Hand-rolled handshake works fine and needs no third-party lib: open TCP to
`127.0.0.1:9050`, greet `\x05\x02\x00\x02` (offer no-auth + user/pass), send
`\x01 <len> <user> \x01 x` if user/pass is selected, then
`\x05\x01\x00\x01 <4-byte IP> <2-byte port>` and check reply byte 1 == `0x00`.
Send `HEAD / HTTP/1.0` to grab a banner. Scan a handful of ports with a small
thread pool; Tor's exit policy refuses some ports, which shows up as failure
rather than a clean negative.
