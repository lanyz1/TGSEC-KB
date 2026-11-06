# Jump-host runners: throughput law and blind-log trap

Applies to any long unattended job driven through a jump host / relay runner
(`rex2.py`-style: push a script to a host, run it, stream stdout home).

## 1. The runner blocks — an empty local log is NOT a hang

Typical runner shape: `c.exec_command(cmd)` then `print(out.read())`.
`out.read()` blocks until **EOF**, i.e. until the remote command exits. So the
local redirected log (`> run.log`) stays **0 bytes for the entire run** and only
fills at the very end.

**Do not diagnose this as a hang, a dead login, or a captcha loop.** In this
session that misread nearly caused a job to be killed and restarted from
scratch. Instead:

- Confirm liveness by looking at the **remote artifact**, not local stdout:
  run a tiny probe that prints the size + mtime of the output file on the host.
- Take **two samples a few minutes apart** and compute a growth rate. A single
  sample proves nothing; the rate proves health and gives an ETA.
- Optional hardening: have the remote script `print(..., flush=True)` per batch
  *and* write incrementally (`jsonl`, `f.flush()` per batch) so a crash still
  leaves recoverable partial output.

## 2. Fanning out onto one target collapses throughput (28x in this session)

Measured on a small PHP/MySQL target:

| workers | per-worker rate | aggregate |
|---|---|---|
| 1 | ~137-163 rows/min | ~150 rows/min |
| 6 | **~6 rows/min** | ~36 rows/min |

More workers made the job **4x slower in aggregate**. The bottleneck was
target-side (WAF rate accounting + DB/app contention), not worker-side. Adding
shards is only a win when the bottleneck is the worker's own link.

**Rules:**
- Before sharding, measure single-worker throughput for a few minutes and check
  whether it is target-bound (slow per-request latency that *rises* with
  concurrency) or worker-bound.
- Shard by **rotating exit IPs** (one worker per egress), not by stacking
  workers behind the same egress. Per-exit accounting means N exits can be
  genuinely additive while N workers on one exit is self-defeating.
- If shards are already running and one correct worker is being starved, the
  redundant ones are not "harmless safety margin" — they actively destroy the
  run. Stop them (with the user's consent — killing processes needs it).

## 3. Growing artifacts must be tail-fetched

If each cycle re-reads a log/response that the job itself is inflating, fetch
cost grows without bound and the capture rate collapses (observed: 93% -> 9%,
because the full-body download was being truncated and the *newest* entries —
the ones you need — were the ones lost).

- Fetch the **tail** with `Range: bytes=-N`, not the whole file.
- Cache-bust every fetch (`?cb=<ms>` / `Cache-Control: no-cache`) when the
  artifact sits behind a CDN/WAF — a cached body returns stale values silently.
- Prefer unique-per-unit markers so that a stale/missing fetch degrades to
  *absent* rather than *wrong* (missing is recoverable; wrong is invisible).

## 4. Do not misread an empty log as "login failed"

A captcha-retry login loop and a blocked stdout look identical from outside.
Distinguish by checking the remote artifact: if the output file has rows, login
succeeded and work is happening. Log lines like `try 0 ... 验证码错误` followed
later by `LOGIN_OK` are normal retry noise, not failure.

## 5. Cleaning up remote orphans

Killing the local runner does **not** reliably kill the remote process (SIGHUP
is often ignored by a detached `python3 script.py`). After stopping a job:

- Run a small kill script on each host that did work:
  `pkill -f <scriptname>` for each known script name.
- Return code 0 = something was killed, 1 = nothing matched (a free liveness
  signal per pattern).
- Watch for **pkill self-match**: if the killer script's own command line
  contains the pattern, it kills itself. Keep the killer's filename disjoint
  from the patterns it kills.
- Re-list processes on the host afterwards to confirm zero remain.
