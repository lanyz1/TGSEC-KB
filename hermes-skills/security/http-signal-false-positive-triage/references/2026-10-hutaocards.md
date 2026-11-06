# 2026-10 hutaocards/Saturney signal-triage log

Concrete controls that produced negative or downgraded findings. No secrets.

## Main API

- 8 mass-assignment candidates under `/user/*` all returned the same 82-byte
  success body; `getUserInfo` read-back still had `isAdmin=0`. Verdict: catch-all
  mock, not mass assignment.
- `getCardBin?bin=1` and `bin=1'` returned the same real BIN record (658711,
  Discover/HK); no time delay. Verdict: `bin` not in SQL, no SQLi.
- `getCardList?pageNum=1` and `pageNum=1'` identical; `SLEEP(3)` blocked by
  Cloudflare 403. Verdict: no blind SQLi claim.
- `getUserInfo?userId=1` still returned own id 94468. Verdict: parameter ignored,
  no IDOR.

## Vite dev server

- `/@fs/app/package.json?raw`, `package-lock.json?raw`, `vite.config.ts?raw`:
  200 with real source. Fingerprinted Vite 6.4.3, `fs.allow=/app`.
- `.env` and `.git/config`: 200 `text/html` SPA fallback, not file reads.
- `/@fs/etc/passwd`: 403. 6.4.3 contains the relevant fs fixes; version-bypass
  line closed.

## Egress proxies

- 592 public CN proxies; only `36.138.53.26:10017` and `:10019` answered.
- Both returned 403/153 for the target and for `http://example.com/`.
  Verdict: proxy-side block, not target reachability.
- `47.101.198.85:8081` answered JSON but `curl -x` exited 1: a CRM API, not a
  CONNECT proxy.

## WebSocket

- media-api: 9 paths x 6 Origin values all 403, no 101. Verdict: edge blocks
  Upgrade; Origin matrix is not evidence of CSWSH or auth bypass.

## Certificate subdomains

- `admin-musichouse.saturney.cn` and `test-musichouse...` -> 139.186.130.53;
  `cq.saturney.cn` -> 113.206.114.122. Both IPs: 17-port scan, zero open, 3 s
  finish. Verdict: dead CT records.

## Cloudflare edge

- `api.hutaocards.com`: 443 -> 526, 80 -> 301 to https. No second origin.
- `43.156.91.32` Host matrix: 13 names, only `www.saturney.io` answered; the
  rest returned 000. Verdict: vhost/Host-level block, not DNS or host down.
