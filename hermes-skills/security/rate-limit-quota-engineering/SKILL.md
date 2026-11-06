---
name: rate-limit-quota-engineering
description: "Use when a per-IP rate cap throttles brute force."
version: 1.0.0
tags: [rate-limit, 429, quota, throughput, brute-force, enumeration, pacing, proxy-pool]
---

# Rate-Limit Quota Engineering

For surfaces where the answer is capped per source IP (register, login, SMS send, code validation,
license check) and enumeration is the only remaining path. The failure mode this skill prevents is
**spending days of a scarce quota at half the achievable rate while reporting "the platform is
locked down"**.

Related but different: `egress-rotation-and-ban-hygiene` (permanent bans, exit reputation),
`password-spray-lockout-bypass` (account lockouts). This skill is about *sustained throughput
inside a live, non-permanent quota*.

## 1. Measure the bucket — never trust the number

Quotas in your own earlier notes, in a README, or inferred from one slow run are usually wrong by 2×.

- Fire **sequential** requests from ONE verified-clean IP until the first `429`; count the passes.
  Single-threaded, because concurrent probes on the same IP corrupt the count.
- `429` appearing at request #20–22 ⇒ a ~20/min bucket. One case had this target recorded as
  "10/min hard cap" and ran at half capacity for hours on that assumption.
- If the same IP keeps accepting after the first `429` with a slightly slower cadence, it is a token
  bucket with refill, not a hard window — pace to the refill rate rather than resetting per minute.
- Egress the measurement through a proxy, not your own IP: your own IP is usually already blocked
  or holds a stale bucket (it reads as `403`/instant `429` and looks like "no access").

## 2. Split the channel — same IP, several independent quotas

Every layer that counts requests is a separate budget. Find them all; they multiply throughput
without touching the proxy pool.

| Layer | Example | Typical independence |
|---|---|---|
| CDN edge vs origin vhost | `https://host/api/x` vs `https://<origin-ip>/api/<prefix>/x` + `Host: host` | independent (measured 18/min + 8/min on one IP) |
| Route prefix on one vhost | `/api/user/register` vs `/api/jmy/user/register` | test it, often independent |
| HTTP vs HTTPS vhost on same IP | `:80` vs `:443` | usually the same limiter — do not count on it |
| Host header variants | `Host: a.com` vs `Host: b.com` | usually the SAME limiter (verified: swapping Host did not reset) |
| `X-Forwarded-For` / `CF-Connecting-IP` spoof | any | does **not** reset a CF edge limit or an nginx `$remote_addr` limit |

**Verify, do not assume.** Exhaust channel A, send one request on channel B: passes ⇒ independent
quotas. Two more rules learned the hard way:

- A spoofed client-IP header may look effective if you only test *after* the bucket already refilled.
  Exhaust first, then spoof, then read the status.
- The origin often only speaks HTTPS. `http://<origin-ip>/api/...` answers `301`, and a followed
  `301` converts POST → GET, which lands on the nginx SPA catch-all (`200`, HTML) instead of the API
  JSON. That shows up as a clean-looking `oth` bucket with zero information — hit the origin over
  **HTTPS** with the `Host:` header.

## 3. Pace — a 429 is a permanently wasted attempt

Bursting burns quota that never comes back. Measured on the same 54-proxy pool:

- 2 threads/proxy, no pacing → ~8 rps, `lim≈700` (≈30% of every attempt destroyed by 429s).
- 1 thread/proxy paced at `60/bucket` seconds, one channel → ~0 × 429 at equal or better rate.
- Same proxies, two paced channels → ~23 rps theoretical (54 × (18+8)/60).

Adaptive loop per proxy thread: on `429` multiply that thread's gap by 1.5–1.6 (cap at 4× base); on
any non-`429` decay the gap by ×0.97 back toward `60/bucket`. Kill a proxy after 4–5 consecutive
`err`/`oth` so dead exits stop consuming slots.

Classify on the **body**, in this order: token-expired → bad-code → success, before any status-code
branch. A proxy that answers `200` with phpinfo/HTML is a false HIT source; only a JSON success shape
counts (and the pool health check must validate JSON for the same reason).

## 4. The token under test dies to its own refresher

When the code under test is an OTP or one-time token relayed by a human (`SMS → operator → you`):

- Any auto-resend loop invalidates the previously issued code. A 4-minute refresher killed every
  code the operator relayed, because the newest issue overwrote it before it was used — the sweep
  died on its first tick with an `exp` flood and it looked like "the code arrived too late".
- **Kill the refresher before accepting a relayed code.** Re-arm only when relay latency is the true
  bottleneck, and never while a code is in flight.
- Send the code, wait for the relay, start the sweeper immediately — usable life is typically
  ~5 minutes and the first 30–60 s die in handshake warm-up. Warm the pool *before* the code
  arrives (health-check + live list on disk), never after.

## 5. Order the candidate space by hypothesis, not by increment

With ~1,000–5,000 attempts per token, ordering decides success:

1. Platform-default / vanity codes (`888888`, `666666`, `123456`, `518518`, `168888`, …).
2. Zero-padded ID space (`000001`–`000800`) if codes may be `zfill(user_id)`. **Test code #1 first** —
   if any user with id 1 exists, `000001` is valid and the run ends in one request.
3. Cross-platform codes: sibling sites built from the same frontend bundle may share an operator.
4. Random over the full declared space (include leading zeros).

A long clean run over one contiguous range is evidence *against* sequential issuance — record what
range is exhausted and stop re-scanning it.

## 6. When the quota is genuinely the wall

Before reporting "infeasible", confirm you are at `IPs × bucket × usable_seconds`, i.e. actually at
the ceiling. Then the only real levers are more IPs or fewer candidates — say so with numbers
("~1,100 attempts per 5-minute token with 40 live proxies; ~4,600 with dual-channel pacing"), rather
than reporting the endpoint as closed.

## Scripts

- `scripts/paced_sweeper.py` — multi-channel paced sweeper: config JSON in, per-channel rate,
  adaptive 429 backoff, body-order classification, HIT/expiry stop conditions.
- `references/case-jinmaiyuan-buckets.md` — measured bucket/channel numbers from a live case.
