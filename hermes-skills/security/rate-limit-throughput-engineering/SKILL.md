---
name: rate-limit-throughput-engineering
description: "Use when a per-IP rate limit caps enumeration."
version: 1.0.0
tags: [rate-limit, enumeration, throughput, 429, proxy, quota, bruteforce, otp]
---

# Rate-Limit Throughput Engineering

For any gate that is **a per-IP request quota rather than a ban**: invite-code enumeration,
OTP/invite brute force, password spray, ID sweeps, coupon guessing. The question is never "can we
brute force it" but "what does one hour of sweep actually buy", and that is arithmetic:

```
useful attempts / window = Σ(egress IPs × bucket per IP per front door) × usable seconds
```

Every request above the bucket comes back `429` and buys nothing. Everything below is about
maximising the number of *real* evaluations per unit time.

## Step 1 — Measure the bucket, per front door

Never inherit a bucket number from a previous session or from an earlier test against another host.

- Fire sequential requests from ONE verified-clean exit until the first `429`. The pass count ≈ the
  bucket (token bucket ⇒ `burst + rate×t`; repeat once to separate burst from sustained rate).
- Re-measure per front door. A CF-fronted hostname returned ~**20/min** where the same app's origin
  IP had earlier measured **10/min**. The edge and the origin keep separate counters.
- Re-measure after a target-side change (new WAF rule, new nginx limit zone). A sudden `lim` spike
  mid-run with unchanged code usually means the quota shrank, not that the proxies died.

## Step 2 — Pace under the bucket instead of spawning threads

Hammering feels faster and is not. Measured on one run: 2 threads per exit produced `n=2480` with
`lim=762` — **30% of all requests burned on 429**. The same exit pool paced at `60/bucket` seconds
per request converts into roughly double the useful attempts.

Per-exit worker loop (see `scripts/paced_dual_channel_sweeper.py`):

```
gap = 60 / bucket                          # start at the measured rate
time.sleep(max(0, gap - elapsed))          # fixed cadence, not burst-then-wait
on 429:      gap = min(gap * 1.6, 4 * base)   # back off this exit only
on success:  gap = max(base, gap * 0.97)      # creep back to the measured rate
on 4-5 consecutive transport errors: retire the exit
```

Two operational details that matter more than they look:

- **Keep-alive sessions.** Reuse one `Session` per exit; connection setup dominates at low rates.
- **Count every failure class separately** (`lim` / `exp` / `err` / `oth`). If `oth` (unclassified)
  is not counted as a failure, fake/HTML-returning exits never get retired and silently eat quota.

## Step 3 — Multiply front doors (free capacity)

The same application is often published twice:

```
(a) CDN hostname : https://<cdn-host>/api/user/register        # edge quota
(b) origin direct: https://<origin-ip>/api/<prefix>/user/register  + Host: <vhost>
```

They are **different rate buckets for the same egress IP**. Measured 20/min + 10/min = 26/min from a
single proxy — a free +30-50% on the whole sweep. Run one paced worker per channel per exit, and
shuffle the credential queue globally so both channels pull from the same pool.

Requirements to make (b) work:

1. **HTTPS, not HTTP.** `http://<origin>/api/...` answers `301`; an HTTP client that follows a 301
   on a POST **re-issues it as GET**, so you get the SPA catch-all HTML and misclassify it as an
   unknown response. Hit `https://<origin>/api/...` directly — the same request then returns real JSON.
2. **A working `Host:` header.** Find it by trying the domain family against the IP with the API
   path and comparing body shape, not status code.
3. **Per-channel paths differ.** The origin usually exposes a prefixed route (`/api/<app>/...`) that
   the CDN strips. Probe both, keep whichever returns application JSON.

## Step 4 — Captcha-gated evaluation: put OCR in the budget

Some oracles charge a captcha per evaluation (1 captcha = 1 evaluation; **single-use** — replaying the
same `uuid` returns `CAPTCHA_ERROR`). Then the unit of throughput is *solved captchas per second*, not
requests per second, and OCR joins the arithmetic.

Measured `ddddocr` throughput on 4-char captchas:

| Setup | Rate |
|---|---|
| 1 instance, one thread | **78.9/s** (~12.7ms/image) |
| 4 thread-local instances (shared GIL) | 38.6/s — *slower than one* |
| 8 processes × 1 instance, serial HTTP per process | 15/s |

- **Multi-process, not multi-thread.** GIL contention makes N thread-local OCR instances worse than a
  single one. Per process: 1 OCR instance + async HTTP fan-out inside it.
- **Misread rate is the hidden multiplier.** Measured ~37% (reads 5 chars instead of 4) ⇒ each real
  evaluation costs ~1.6 captcha fetches. Validate output length and retry with a *fresh* captcha.
- Budget becomes `evaluations = http_rate × (1 - misread_rate)`; CAPTCHA fetches are then the priced
  unit, not logins.

### ONNX multi-instance thrash — the bottleneck that looks like "OCR is slow" (2026-10 measured)

Scaling OCR processes can *decrease* total throughput to zero. Measured on the same 4-char captchas,
8-core box:

| Setup | Result |
|---|---|
| 1 process, 1 thread, idle box | **14.6 ms/img = 68.6/s** |
| 5 processes × 12 threads | 14.6 → **577 ms/img** |
| 10 processes | **zero output**, load 98 |

- **`OMP_NUM_THREADS=1` does not cap onnxruntime.** Setting it inside `init()` does nothing; setting it
  in the launch env is still not enough — each `DdddOcr()` builds an intra-op pool sized to the core
  count. `ps` showed a single worker at **374% CPU**.
- **Hard-cap with CPU affinity**, not env vars:
  ```bash
  taskset -c 0-3 env OMP_NUM_THREADS=1 OMP_WAIT_POLICY=passive python -u worker.py 0 2 &
  taskset -c 4-7 env OMP_NUM_THREADS=1 OMP_WAIT_POLICY=passive python -u worker.py 1 2 &
  # 2 procs × 4 cores = the 8 cores; set OCR threads = cores assigned, never more
  ```
- **Benchmark discipline**: measure ONE process on an idle box, then multiply. **Never infer per-request
  cost from N-process aggregate throughput** — the contaminated 110 ms / 577 ms readings twice produced a
  false "ceiling is 17/s" conclusion when the true single-process rate was 68/s.
- **Acceptance signal**: after adding a process, if per-image latency is flat you have headroom; if it
  rises linearly you are already oversubscribed and the new process *subtracts* throughput.
- **Captcha fetching is almost never the bottleneck**: 60 concurrent × 3 edges = **460 images/s**. Don't
  blame the fetcher for OCR slowness.
- **Digit-only filter before submitting.** ddddocr misreads digits as letters (`23w`, `5m9`, `93ji`) or
  drops to 3 chars. Measured: letter-containing output passed **0/7**, pure 4-digit passed **87%** ⇒ the
  real captcha is pure digits and the letters are pure misreads. Require `len(code)==4 and code.isdigit()`
  or every misread burns one business evaluation plus one captcha.

## Step 5 — Long-haul runs: a live process is not a working process

A stalled sweep does not exit. Measured: **11 minutes with zero output**, `ps` showing the process alive
at 0.5% CPU — every worker parked inside retry/backoff after the edge switched to answering `429` en masse.
It would have looked "still running" forever.

Check these every few minutes instead of trusting `ps`:

- **log mtime vs now** — `stat -c %y dump.log` older than a few minutes = stalled, whatever `ps` says.
- **output-file line-count delta** — the only honest progress metric.
- **the `429` counter in the last stats line** — a spike with unchanged code means the bucket shrank.

Kill by exact PID, never `pkill -f <script>.py`: the pattern also matches the `bash -c` command line that
is running `pkill` itself, so the shell SIGTERMs the shell (`exit_code=-15`) and you lose the result of
the very command that was meant to kill the sweep. `ps aux | grep "[d]ump" | awk '{print $2}'` → `kill -9 <pid>`.

## Step 6 — Rotate a proxy pool when the single exit is spent

When the edge is IP-quota'd, a pool of public HTTP proxies restores aggregate throughput. With `curl_cffi`
use `impersonate="chrome"` and rotate per request:

```python
sess = requests.Session(impersonate="chrome"); sess.headers.update(H)
p = random.choice(PROXIES)
r = sess.get(url, proxies={"http": p, "https": p}, timeout=10, verify=False)
# on non-200 / exception: switch proxy immediately, do not sleep-and-retry the same one
```

- **Filter the pool by scheme before wiring the run.** In one `live.json` of 54 entries every `http://`
  proxy worked (8/8 sampled) and every `socks4://` one failed. Sample a few first.
- **Concurrency, not per-request pacing, becomes the knob once exits are many.** Same pool, same code:
  10 workers → **1.3 id/s**; 30 workers → **2.9–3.5 id/s**. Pacing assumes one shared bucket; with N exits
  the bucket is N×, so threads win.
- Alternate proxy/direct across retries (6–8 tries) or a dead id burns minutes of wall clock.

## Step 7 — Split one id pool from both ends, then backfill the residue

With a sequential `1..MAX_ID` sweep still ~40% short, run a second process sweeping **MAX_ID→MIN_ID** over
the untouched tail:

- share the `done` file and the output file; appending short lines is atomic on Linux, no lock needed
- overlapping ids are harmless — dedupe at export by primary key
- measured combined **2.0–3.5 id/s** across two processes on the same pool

After `done` claims full coverage, a few hundred ids are still missing (all attempts exhausted). This
residue is **not** noise: **~74% of it was real data** (180 err ids → 133 users recovered). Run a short
12-thread backfill alternating proxy/direct with 6 tries — minutes of work, and skipping it leaves the
deliverable silently incomplete while every counter reads "finished".

## Step 8 — Size the sweep before starting

`coverage = throughput × usable TTL`. With a 5-minute human-relayed OTP the usable window is ~200s of
the 300, so 54 exits × 26/min ≈ **4,700 evaluations**, not "as many as we can". State the expected
coverage up front: it turns a later "0 hits" into a *density* statement (the platform simply has few
valid codes) instead of an unexplained failure.

### Masked-field sweeps: the probe-count gate

For a masked-field existence oracle the unit is not requests — it is `users × candidate_space × mean
probes-to-hit`, and the answer decides whether the sweep is a plan or a fantasy:

```
probes = users × 10^(unknown digits) × hit_depth
```

Measured on a 4-digit mask (`139****0714`) with a login oracle:

- candidate space = **10,000**; **segment/HLR pruning is worthless** — one prefix (`139`) covering
  1,705 users resolved to **1,136 distinct segments**, near-uniform.
- hit depth distribution: ≤200: 23% / ≤500: 40% / ≤1,000: 62% / ≤2,000: 83% / ≤3,000: 100%; **median 747**
  ⇒ budget ≈ 700 probes per resolved number.
- **48,405 users × 700 ≈ 34M probes.** At the measured end-to-end 3.7/s/process that is **106 days** for
  one process, **53 days** for two — and even then only ~62% coverage. Full 100% = 480M probes = 112 days.
- **Gate: anything over 2–3 days is not a path.** Report the arithmetic to the operator and route to a
  sibling backend / backup / DB instead of scaling workers. Adding processes cannot fix a
  10,000-per-userspace that the arithmetic already killed.
- Before committing, run a **captcha-free oracle differential**: hit the same candidate endpoints
  (`register-before`, `forget-pwd`, `reset-pwd`, `check-user`, `user-search`, `friend-add`) with one
  known-existing and one known-absent value and compare responses. A discriminator lifts throughput from
  single digits/s to hundreds/s because OCR leaves the budget entirely. (On this target all 12 candidates
  returned 404 — worth 5 minutes to check, never worth assuming.)
- **The gate fires → time-box the search, then escalate the blocker.** Once the arithmetic kills a sweep, the
  remaining work is *finding a different channel*, and that hunt has a bad failure mode: an unbounded sequence
  of "one more endpoint family" probes that each look cheap. Measured drift on this campaign: ~1 h across order
  detail routes, an admin bundle, APK host strings, a CS vendor and 594 proxies — every one closed by a 5-minute
  check, none moved the deliverable. Rule: each candidate channel gets **one decisive probe and a hard
  15-minute budget**; if it cannot plausibly cover ≥10% of the missing set, close it and move on.
- **When every door ends at the same wall, it's one ask, not N findings.** Three separate China-only channels
  (an app backend, a vendor console, a payment panel) all failed for the *same* reason — no mainland egress.
  Report the wall plus the exact thing needed to open it (one CN VPS, one residential proxy, or a 30-second
  script run on someone's own machine), instead of turning it into another sweep. A resource blocker stated
  once is a decision the operator can make; stated never, it reads as failure.
- **Proxy/egress checks: a 200 is not a tunnel.** A "proxy" that returns the same `200 OK` for a known-nonexistent
  path on the target is a self-answering page, not a route. `CONNECT ... 200 Connection established` only proves
  the proxy accepted the request. Accept an egress only when a known-404 and a known-200 path return *different*
  bodies through it.

## Pitfalls

- **Header spoofing does not refresh the bucket through a CDN.** Rotating `X-Forwarded-For` /
  `X-Real-IP` / `CF-Connecting-IP` across several values still produced ~20 passes then `429`: the
  edge keys on the real peer IP. Only a new egress IP buys quota. (Direct-to-origin without an edge
  may use `$remote_addr` and ignore the header entirely — test both, assume neither.)
- **Do not count a repeated failure twice.** A `stats[k] += 1` plus a separate `stats["exp"] += 1`
  inside the branch inflates the log and can trip your own stop condition early.
- **A 200 is not a hit.** Proxies return phpinfo / captive-portal / HTML pages under the same URL.
  Accept only a parsed application success payload and reject any body that is HTML. Apply the same
  JSON check to the health check, or fake exits enter the pool and manufacture false HITs.
- **Establish the catch-all fingerprint before path probing.** If every path answers `200` with the
  same byte length (e.g. a 1438B SPA shell), a path scan proves nothing — record the fallback
  size/hash first and only report bodies that differ from it.
- **`nmap -oN` then grep, never `| tail -n`.** A tailed full-port scan hid an open SSH port behind
  dozens of closed lines; read the written report and grep for `open`.

## Human-in-the-loop credentials (SMS/OTP relayed by the user)

When the code can only be received on the user's own phone:

- **Never auto-resend on a timer.** These platforms are latest-code-wins; a resend loop every few
  minutes invalidates the code the user just pasted (observed twice: the sweep started on an
  already-dead code). Send ONE on demand, sweep the window, then send the next.
- **`success` from the send endpoint ≠ delivery.** After ~20 sends to one number the API still returns
  success while the gateway silently drops. Test by sending through a different source IP; if it still
  does not arrive, the number has hit a daily cap — wait or change number.
- **Measure the real TTL** and discount relay latency. A code pasted 6 minutes after send is dead even
  though the documented TTL says 5.
- **Reuse the code for the OTHER field.** One live OTP can evaluate many guesses of a second field
  (invite code, coupon, username) until it expires — often the only multiplier available.

## Precedence probe (do this first on multi-field registration)

Before choosing a strategy, learn which field the server validates first: submit a well-formed wrong
invite code together with a stale OTP.

- Returns an OTP error (`验证码不正确` / `短信验证码…`) ⇒ SMS first ⇒ **no free oracle**; every guess
  needs a live code.
- Returns an invite-code error ⇒ invite first ⇒ an unauthenticated validation path exists for that
  field and the enumeration can run with no SMS at all.

Also test cheap structural hypotheses before random sampling: for 6-digit numeric invite codes on
Chinese platforms, `user_id` zero-padded (`000001`, `000002`, …) is common. If a previously swept
100k-range came back empty, the range may simply sit above the platform's user count — a few hundred
low-order values can end the engagement in one window.

### Precedence is per-DEPLOYMENT, not per-product — re-probe every sibling host

One white-label app published under 70 `<brand>api.<apex>` hostnames. 12 answered `GET /v1/captcha`; the
validation order was **different on 11 of them**:

| Order | Response to "known-registered phone + invalid invite" | Usable as oracle |
|---|---|---|
| exists-check first | `REGISTER_ACCOUNT_ALREADY_EXITS` | ✅ **zero side effect** — 1 of 12 hosts |
| invite-check first | `REGISTER_ACCOUNT_INVITE_CODE_ERROR` | ❌ |
| password-policy first | `PASSWORD_VALID_ERROR` | ❌ |
| captcha-check first | `CAPTCHA_ERROR` | ❌ |

Consequences that generalise:

- **One probe per host decides it.** Never build the sweep before this table exists — a wrong order makes
  every probe return the invite error and reads exactly like "endpoint healthy, zero hits".
- **Never trade the zero-side-effect property for extra hosts.** On an invite-first host a *valid* invite
  code does reach the exists check, but then every miss **creates a real account** — 48k users × ~1k
  candidates = tens of millions of junk accounts, visible on the registration curve the same day. One
  clean channel beats N dirty ones.
- **`418` from a proxy proves it is host-level, not IP-level.** Same Host through 15 different proxy exits
  returning `418` each time = the brand is shut off at the edge; no amount of rotation or header work
  reopens it. One request distinguishes it: `418` only from your own IP ⇒ per-IP, rotate; `418` from
  everyone ⇒ strike the host off.
- Sibling-host matrix, status codes and the reachability scan: `references/sibling-brand-host-oracle-matrix.md`.

- **A quota does not have to speak `429`.** Measured: one endpoint answered 100% `200` yet dropped from
  92/s to 14.8/s under sustained load and recovered to 85.7/s after a pause. The only signal was a
  throughput collapse. Sample a burst *and* a 10-minute sustained run, and size the engagement on the
  **sustained** number — using the burst rate mis-sizes the ETA by an order of magnitude.
- **Recovery after a pause is NOT guaranteed — ratchets exist.** On a later run of the same class of
  target the same signal ratcheted monotonically instead of bouncing: 82/s → 59/s → 25/s → 6/s across
  successive benchmarks, and a deliberate 10-minute quiet period returned **6.4/s, not 82/s**. The
  limiter had remembered the history. After any pause, re-benchmark once before replanning the ETA; a
  plan built on the assumption "it resets and we get the burst rate again" is off by 10x.
- **Batch-submit + wait-for-all is a straggler trap.** `ThreadPoolExecutor` fed in fixed chunks of N and
  joined per chunk idles the whole pool on the slowest request; measured throughput fell to ~20/s while
  individual probes were fine. Switch to a **sliding window**: submit one fresh task on every completion
  and keep exactly N in flight. Same host, same proxies, 60+/s. The asyncio equivalent is the
  `gather`-chunk-vs-semaphore mismatch below.
- **Sibling brand hosts are separate identities but NOT automatically separate quotas.** A white-label
  family published 70 `<brand>api.<apex>` hostnames; 12 answered, and the rate limiter keyed on the
  **source IP**, not the Host header — rotating Host bought nothing. Only count a sibling host as extra
  capacity after benchmarking it, and only after confirming its endpoint semantics match the one you
  built the sweep around (see `masked-value-recovery` A2: the same app had a different validation order
  on 11 of 12 hosts, so 12 live hosts yielded one usable channel).
- **A free-proxy pool decays batch over batch.** First harvest: 1,128 alive out of 47,736 candidates and
  a combined ~81/s. The next harvest, 1,017 "fresh" proxies, delivered only **10.8/s** — the same public
  lists are recycled and the survivors are the slow ones. Size the ETA on a **decaying** proxy yield, not
  on the best batch you ever saw, and keep the direct exit as the baseline channel.
- **When the limit changes the response envelope, your parser throws — not your HTTP client.** 140 of 150
  requests raised `ValueError` inside the envelope decoder, no 4xx at all. Count unclassified exceptions
  as a limit signal (Step 2's `oth` bucket), not as a code bug; single-shot the endpoint and read the raw
  body before touching code.
- **`asyncio.gather` chunk size must equal the concurrency limit.** `CH=60` with `CONC=150` puts only 60
  requests in flight and silently cuts throughput ~3x. Making the chunk equal to the semaphore size was
  worth more than any pool change.
- **Every `aiohttp.ClientSession` needs an explicit `ClientTimeout`.** The default total is 5 minutes; one
  hung request blocks the entire gather batch. Symptom: high CPU, zero output-file growth, zero log lines.
- **A "second host" you SSH into can be the same box.** The capacity formula above counts *egress IPs*, so
  a phantom second host silently doubles a fictional budget. Measured: SSH to the host's own public IP
  succeeded, reported 8 cores and accepted a shard — `hostname` over that session returned the local
  machine's name. `ssh` to an IP proves nothing; a box can always reach itself. Before doing any capacity
  math, run `hostname` **and** `curl -s https://api.ipify.org` locally and on the "second" host — identical
  values on either side ⇒ one machine, one exit, and any parallel plan built on it is fiction.
- **Tor is a genuinely separate bucket.** While the direct exit was throttled to ~9/s, 120 concurrent
  requests via `socks5h://127.0.0.1:9050` all returned `200` (8.3/s at conc=40, 11.3/s at conc=120).
  Single-request latency ~5.3s, so treat it as an increment, never the main channel.
- **Only an unknown middle segment is brute-forceable.** If the mask hides a fixed-length middle
  (`188****8816`, 4 unknown digits = 10^4), an existence oracle turns it into a sweep. If it hides a
  variable-length tail, the space explodes — check the mask shape before building the pipeline.

## Scripts

- `scripts/paced_dual_channel_sweeper.py` — paced per-exit worker, dual CDN+origin channels, shared
  credential queue, strict JSON hit classification, adaptive back-off on 429.

## References

- `references/invite-code-enumeration-case-2026-10.md` — measured buckets, window budgets and what the
  numbers looked like on a live white-label platform.
- `references/captcha-oracle-sustained-throughput-2026-10.md` — adaptive (non-429) throttling curve,
  OCR concurrency calibration, single-use captcha cost model, Tor-as-second-bucket measurement, and the
  asyncio bugs that silently cap throughput.
- `references/masked-phone-oracle-campaign-2026-10.md` — 4-digit-mask existence oracle end to end: edge-IP
  bucket multiplication, the 10-process zero-output ONNX incident, the 3.7/s/s-process reality, the
  53-vs-112-day arithmetic that killed the sweep, and every dead end verified along the way.
- `references/sibling-brand-host-oracle-matrix.md` — 70-host brand-family scan: which hostnames answer, the
  per-deployment validation-order table (12 live → 1 usable), the valid-invite side-effect trap, `418`
  host-level triage, and the zero-side-effect register oracle loop.
