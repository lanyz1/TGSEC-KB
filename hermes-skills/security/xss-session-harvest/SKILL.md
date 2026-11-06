---
name: xss-session-harvest
description: "Use when harvesting operator sessions via stored XSS."
version: 0.1.0
tags: [xss, session-harvest, admin-panel, payload-delivery, https-hook]
related_skills: [c2-infrastructure-pentest, pentest-execution, waf-evasion-and-credential-attack]
---

# XSS session harvest (operator / admin consoles)

Goal: the human operator's browser executes your payload inside the console's origin, and the
console's session, tokens, and API data land on a hook you control. **Silent failure is the norm** —
a chain that skips ANY of the four preflights below reports zero hits while looking perfectly armed.

## When to use

- A hardened console is the target: admin routes are decoys (uniform `{"ok":…}` stubs), nginx 405s
the sensitive routes, or the panel is not publicly proxied — the operator's browser is the
remaining entry, and stored XSS is the play.
- Any stored-XSS surface that feeds an operator UI (C2 consoles, management dashboards, live logs).
- The console's credential login is locked out, rate-limited, or 2FA-gated and you can write into a
  surface the operator views: a LIVE session captured from the panel bypasses every credential
  control (session ≠ password). The login lock is not the door.

Don't use for: reflected XSS against anonymous victims; use `web-sec` / `hack-skills` for generic
XSS playbooks.

## Preflight — the four silent killers

1. **HTTPS or nothing.** If the console is served over HTTPS (any Cloudflare-fronted panel is),
   HTTP payload URLs are dead on arrival: `<script src="http://…">` is blocked as active mixed
   content, and `<img>` beacons are auto-upgraded to https:// and fail the TLS handshake. Serve the
   payload script AND the callback from one real-TLS endpoint. Zero-setup route on an attacker box
   with a public IP: `certbot certonly --standalone -d <IP>.sslip.io` — `<IP>.sslip.io` resolves to
   the IP itself and can hold a real LE cert over HTTP-01. Check for an existing
   `/etc/letsencrypt/live/<IP>.sslip.io/` cert first: earlier engagements on the same box often
   leave one behind.
2. **Audit the render code before firing.** Get the console's HTML/JS (repo mirror, source leak, or
   capture) and grep `innerHTML`, `textContent`, `esc(`, and template interpolations. Payloads
   landing in `esc()`-wrapped fields never fire — wasted shots also burn the vector (operators
   purge rows and harden once they notice). Read helper bodies before trusting a name: a helper
   with a fallback argument (`nf(x,'?')`, `fmt(x,'-')`) is a null-formatter, not an escaper.
3. **Prefer auto-fire sinks over click sinks.** Attribute-context injection renders and executes
   with no interaction: any `attr="'+field+'"` (e.g. `title="'+device_uid+'"`) lets a value
   `"><img src=x onerror=…>` break out on render. Table cells `<td>'+field+'</td>` are also
   auto-fire. `onclick="f('field')"` only fires on a click — keep it as backup, not the plan. **Match payload shape to the insertion method — grep the page's JS for `innerHTML =` / `insertAdjacentHTML` before firing.** HTML assembled as a string and assigned via `innerHTML`/`insertAdjacentHTML` inserts `<script>` elements INERT (they never execute); fire event-driven tags instead (`<img src=x onerror=…>`, `<svg onload=…>`), or an inline handler that creates and appends the real loader (`document.createElement('script')`).
4. **Self-test end-to-end before declaring armed.** From the public internet, fetch the payload URL
   and hit the callback path; confirm BOTH land in the hook log. If the hook cannot see your own
   test, it will not see the operator's.

## Payload chain

- Harvester: `templates/harvester.js` — captures `document.cookie` + `localStorage` +
  `sessionStorage` + `window.CSRF_TOKEN` + a first-screen HTML snapshot, then runs a credentialed
  fetch sweep over the console's own API paths. `document.cookie` misses HttpOnly session cookies —
  the `credentials:'include'` sweep is the actual session-takeover mechanism, not cookie capture.
- Exfil in ~900-char chunks via `new Image().src` to `/ce?...` (no CORS needed; more resistant than
  fetch). Send a single `FIRE=1` beacon first so bare execution is distinguishable from a full run.
- Cache-bust the script URL (`?t='+Date.now()`) so the operator always loads the newest payload.
- **Stored rows pin the payload host as-of-injection.** Changing hosts (http→https, IP→domain)
  orphans every already-stored row — re-fire fresh injections after any host change. Edits behind
  the SAME URL (swap the served file's contents) reach the operator without re-injection.
- Serve script and callbacks from the same HTTPS host (`https://<IP>.sslip.io/x.js`).

## Injection surface (writing into the console's store)

- Feed payloads through every write endpoint the platform exposes to its clients —
  beacon/checkin/exfil/visit/ip-sync style channels — because those fields surface in the
  operator console's tables and details views. **Public business write-APIs count too: an order /
  ticket / registration `create` endpoint you can call anonymously on a payment dashboard or utility
  panel feeds the operator's own back-office tables — a delivery channel, not just a data leak.**
- **Seed the log/telemetry feed first.** Console pages that render log streams (chain logs, live
  logs, event feeds) usually `innerHTML` message/device fields and auto-refresh — the
  most-watched, least-hardened surface. Reproduce the exact write shape the viewer page itself
  uses (copy from its source or its own fetches, e.g. `?type=sdk&msg=<payload>`) so the entry
  parses and renders instead of being dropped as malformed.
- **Aim at the operator's ALERT page, not the archive.** Queues that auto-refresh and play a
  sound/notification on new entries (incoming payments/orders, new-device feeds) are opened within
  minutes of a new row; a write you can make anonymously forces the render. Confirm from the page's
  JS that the poller fetches full records, not just a count.
- Fire a spread, not a single shot: same payload across multiple fields AND multiple contexts
  (one field in an attribute context, another in a cell context, a third in a title attribute,
  plus exfil values).
- Keep a dated log of which channel/field each shot targeted — a later hit must map back to the
  surface that carried it.
- **Direct-to-operator message APIs are bait channels.** A DM/send endpoint that validates recipients ("no such user" vs delivered) doubles as an existence oracle for every account — including the operator's own admin account — and delivers a message into that inbox. When the operator UI renders direct messages, a minimal beacon inside one plausible-looking message is one more planted surface; keep the shot count tiny (send endpoints are usually rate-limited and spam is operator-noticeable).

## WAF-aware payload shaping & submission discipline

- **Separator variants beat signature filters.** CN store-front WAFs (vendor "…wall" filters) match
  canonical tag syntax, not the HTML5 parser's full grammar: `<img src=x onerror=…>` → 403 while
  `<img/src=x/onerror=…>` (slash as attribute separator) → 200 — and it executes in mainstream
  browsers. On a 403, walk separator/case variants (slash, tab, newline; tag and attribute case)
  before downgrading the payload.
- **Separate endpoint-walls from payload-walls first.** Submit a clean body: if it also fails
  (204/403), the rule targets the ENDPOINT (Cloudflare-class), not your payload — stop reshaping
  and change channel (other path/host/instance). If clean passes, map the filter one attribute per
  shot so a failure names the token that trips it.
- **Fetch the hidden token fresh for every submission** (these forms carry
  `token = md5(session-stuff) + timestamp`); a stale token drops silently. Test BOTH urlencoded and
  multipart bodies — they hit different filter stages.
- **Verify raw storage before declaring armed**: source-read the write path (`input('desc/s')` →
  direct insert) AND the viewer template (raw `{$var}` echo, no escaping helper). Accepted
  submissions prove nothing — 5/5 200s can still be dead at render.
- **Read what the write DOES besides storing.** Complaint/report forms on CN card-shop families
  freeze the referenced order and claw back the seller's settled balance — every shot moves real
  state. Keep the shot count minimal and the visible copy plausible.

## Hook listener

`templates/https_hook_listener.py` — one TLS listener serves both the payload route and the
callback route, appending every hit as JSON lines with a real/noise classifier (cookie non-empty,
marker paths, magic bytes).

- Kill any stale listener on the port before starting (a leftover server on :443 blocks yours).
- Public hook ports get scanned within minutes of opening. Alert on a DISTINCTIVE MARKER path
  (`/HIT?…`) in the payload, not on raw log growth — unfiltered growth-alerts fire on scanner
  noise. Wrap the watcher as marker-count → alert → exit (reusable: `scripts/oob_hit_watch.sh`),
  so a notify-on-exit job reports the hit without polling. **Count markers with `awk` + `wc -l` (the bundled script does):** `$(grep -c MARKER log || echo 0)` captures `"0\n0"` on zero matches — `grep -c` prints `0` AND exits `1`, so the fallback fires too — and every numeric compare in the loop then errors out as false (`[: integer expression expected` spam in the job log, watcher silently never fires).
- Wrap TLS per-connection inside the handler thread; wrapping the listening socket lets a single
  non-handshaking scanner stall the accept queue and kill every callback.
- After edits, reload and re-run the self-test.

## Success criteria

- A hit in the hook log from a NON-attacker IP with the `FIRE` marker. Reachable ≠ authorized ≠
  effect: only operator-origin data counts (same reporting standard as other campaigns).
- Escaped-field misses and mixed-content blocks are INVISIBLE failures — before concluding "the
  operator never opened the panel", re-audit every injected field against the render code and
  confirm the end-to-end self-test from an external vantage.
