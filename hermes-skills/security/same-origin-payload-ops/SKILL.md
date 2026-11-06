---
name: same-origin-payload-ops
description: "Use when planting a payload with no external hook."
version: 0.1.0
tags: [payload-delivery, session-harvest, exfil, cdp, admin-console]
related_skills: [xss-session-harvest, stored-xss-operator-honeypot, same-origin-upload-xss, pentest-execution]
---

# Same-origin payload ops (no external hook)

A hardened console whose credential login is locked, 2FA-gated, or simply unknown. The remaining
door is the operator's own browser. This card covers the variant where you have **no public
listener, no TLS cert, no DNS** — the whole chain lives on the target's origin, and the loot comes
back through the target's own authenticated API.

Use `xss-session-harvest` when you need an injection sink and an HTTPS hook. Use this card when the
app itself gives you an upload surface and a free-text write API — far more common than a clean
stored-XSS sink on a modern Vue/React console.

## Pre-flight: what will the stolen token actually unlock

Do this BEFORE spending an operator click, because a wrong path in the payload is an invisible miss.

1. Pull every admin route out of the admin SPA bundle (`grep -rhoE '/api/admin/[a-zA-Z0-9/_-]+'`).
2. GET each with a **normal low-privilege user token** and classify:
   - `200` + data → broken access control, the sweep is already won; stop and exploit it.
   - `401`/`403` → path exists and is role-gated. Good payload targets.
   - `404` → wrong path or different router (method-specific 404 is common on Go net/http). Fix it now.
3. Skip destructive verbs (`delete|remove|clear|reset|import|execute|run|send`) in the sweep — a
   mistaken 200 on a delete is an own-goal.
4. Names that matter once you hold an admin token: admin list (often carries plaintext TOTP seeds),
   user list, agent list, and the review-queue list (carries real name / ID card / bank card).

## Delivery: the attachment polyglot

Upload endpoints that validate images by magic bytes accept `PNG header + HTML body` under a `.html`
filename. The stored file is served `Content-Type: text/html` from the console's own origin, so it
executes with full same-origin access to `localStorage`.

- Plant it wherever a human is **forced to review an attachment**: voucher/receipt images, KYC photos,
  ticket attachments, dispute evidence. The review queue beats a chat message — chat clients render
  URLs as plain text, while an image thumbnail is a click target by design.
- Pretext that forces the click: *"the voucher image failed to render, open the original to verify"* —
  the thumbnail is genuinely broken (it is HTML), so the story matches what the operator sees.
- Submit a spread of rows, not one. Queues sort newest-first; the plant should be the first thing the
  morning shift sees. Vary the wording slightly; keep each one plausible and boring.
- Verify the served object before declaring armed: `curl -I` must show `text/html` and no
  `Content-Disposition: attachment`. Then confirm the `<script>` survives after the PNG bytes.

**Multipart gotcha:** if the HTTP session carries a global `Content-Type: application/json`, `files=`
uploads go out with the wrong boundary and the server answers "please select an image file". That is
a client-side false negative, not a server control. Use a clean session for multipart.

## Payload: steal, then spend the token inside the same execution

A token alone is fragile (short TTL, session rotation). The payload should use it immediately:

1. Read every token-ish key from `localStorage` / `sessionStorage` / `document.cookie`.
2. Exfil the raw token first, as its own marker, so a partial run still yields the session.
3. Then `fetch` the pre-flighted admin endpoints with the stolen token and exfil each response,
   chunked. One click should return admin list, user page, and review-queue page — not just a
   string you have to race to use.
4. End by redirecting to the real console path after ~8s, so the operator reads it as a glitch.

Template: `templates/same_origin_harvester.html` (placeholders only, no target values).

## Exfil: the target's own API as the drop box

With no listener, register an account on the same app and use a free-text write endpoint (address
book, notes, feedback, profile remark) as append-only storage:

- Payload logs in as that account, then POSTs `base64(chunk)` into the field. ~190 chars per row;
  cap ~40 rows per stream to stay under any per-account record limit.
- A marker prefix per stream (`SYS_TOK_0`, `SYS_USERS_0`, …) makes reassembly mechanical and lets a
  watcher filter noise.
- Poll the account from your side and reassemble. Collector: `scripts/selfapi_collector.py`.

**Collector rules, each learned by breaking it:**
- List APIs return **newest-first**. Sort ascending by id before processing, or a session's header
  marker arrives after its own data chunks and the pool is cleared at the wrong moment.
- Record a **baseline id** at startup and skip everything at/below it, or the first poll replays your
  own self-test rows and overwrites fresh loot.
- Clear the chunk pool on the session's first marker (the `_0` of the token stream).
- Completion = a chunk **shorter than the fixed slice** (the tail). Only then log `SAVED`; log `PART`
  for intermediate chunks, or a notify-on-pattern watcher fires on every single chunk.
- Base64 padding: re-pad with `"=" * ((4 - len(s) % 4) % 4)` before decoding partial buffers.

## Validation: real browser, not curl

Curl proves the file is served; it does not prove the payload runs or that its fetch paths exist.
Headless Chromium + CDP does, in about 20 seconds:

1. Launch: `chromium --headless=new --no-sandbox --disable-dev-shm-usage --user-data-dir=/tmp/cprof
   --remote-debugging-port=9223` (throwaway profile when the shared one is wedged).
2. `GET http://127.0.0.1:9223/json` → `webSocketDebuggerUrl`.
3. `Page.navigate` to the origin, wait, then `Runtime.evaluate` to write a marker token into
   `localStorage`.
4. `Page.navigate` to the payload URL, wait ~12s.
5. Read the exfil store and confirm: token marker + one row per admin endpoint.
   A `404 page not found` in an exfil row means the payload is firing but the path is wrong — fix the
   payload, not the delivery.

Harness: `scripts/cdp_payload_e2e.py`. Syntax-check the extracted script with `node --check` before
uploading; one unbalanced brace wastes a whole plant.

## Timing and operational discipline

- **Plant to the operator's clock.** A review queue filled at 03:00 local sits untouched until the
  morning shift. Convert: Beijing 09:00 = 01:00 UTC. Fill the queue shortly before their day starts.
- Review flows that auto-advance status (submitted → reviewing → paid) are theatre, not human review.
  Do not read auto-progress as "someone looked at my attachment".
- **Never probe a locked account.** On a 4-attempts/30-min lock, case/whitespace/unicode variants
  share one counter, and any request during the lock **resets the 30-minute timer**. Nonexistent
  usernames lock too, so lock behaviour is not a username oracle. One careless variant sweep costs
  another half hour; a locked login is not the door anyway — the session is.
- Keep the low-priv account used for route probes separate from the account the payload logs into.
