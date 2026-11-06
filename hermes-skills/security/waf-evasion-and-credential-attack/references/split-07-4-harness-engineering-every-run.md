## 4. Harness engineering (every run)

- **Hit detection must be a POSITIVE match on success markers only.** Classifying "anything that is
not the wrong-credential string" as a hit scores CDN/gateway error pages (a Cloudflare 502 body)
as passwords and aborts the run on garbage. Classify every response as: wrong / rate-limited /
lockout / transport-error / **unknown**; append unknown bodies to a side file for review, never
treat them as hits.
- **Never open the log file inside the worker loop.** `open(log,'a')` per N attempts leaks
descriptors and a 100-thread run dies within seconds with `OSError: [Errno 24] Too many open
files`. Print with `flush=True` and let the shell redirect, or use `with open(...)` per write.
Raise `ulimit -n` before launching.
- **Prefer a shared atomic index over a producer/consumer queue.**
`with LOCK: w = WORDS[IDX[0]]; IDX[0] += 1` cannot drain early and gives an exact resume point.
Queue + `get_nowait()` worker pools exit the whole pool prematurely and lose their position
silently — the run "completes" after a few thousand words.
- Log the **index**, not just the attempt counter; the index is what a resume starts from.
- Wrap each request in try/except and `continue`; one transport exception must not kill a worker.
- Kill a previous run through a reusable killer script, never a raw inline `pkill -f <pattern>`:
the invoking shell's own command line contains the pattern and gets SIGTERM'd — bracket-tricks and
grep-into-kill loops self-kill too. Working shape: a script that runs `pkill -9 -f "$PAT" --older 3`
(the fresh invoking process is under the age threshold, so it is excluded), repeats once, then lists
what survived by PID for a manual `kill -9`.
- **Wrap the WHOLE worker body, not just each request.** One shared helper raising (a renamed
import, a schema change) kills every parallel worker one at a time; the signature is counters frozen
at zero while the token/candidate queue stays full. try/except around the full loop iteration +
traceback print + a heartbeat stats line (attempts / rejected / no-response / no-token) every cycle
makes the stall visible in seconds. Also wrap each attempt in an overall deadline (e.g.
`asyncio.wait_for(...)`), and never `await sleep()` inside a shared lock — the sleep holds the lock
and serializes every worker behind it.
- **A file patch does not reach a running process.** After editing a script, kill and relaunch it —
otherwise the old code keeps running and you debug behavior the new code already fixed.
- Poll progress in short increments — a foreground sleep longer than the tool's cap terminates the
command (the background job survives; you just lose that call's output).
- Resume from the recorded index rather than restarting the dictionary; re-testing candidates is
wasted attempts against a quota.
- **Captcha-gated endpoints: one solve = one attempt, and a rejected solve must NOT consume a
candidate.** When login/register starts answering "complete the captcha" (`captchaVerifyResult:false`,
"upgrade your app"-style errors), solve→submit 1:1 (tokens are single-use); on a rejected solution
retry the SAME candidate with a fresh solve instead of advancing the index — advancing on rejects
silently skips candidates and corrupts the resume point.
- **Decouple solvers from consumers via a file queue.** N headless-browser solver workers write
tokens into a queue directory (claim by atomic rename; TTL ~120s); the brute consumes them.
Solver throughput (~one 7-10s solve per worker) is the campaign ceiling — size the run by it.
- **The captcha vendor rate-limits solving itself.** Acceptance degrades under volume (measured
~50% rejects after a few hundred solves from one IP/fingerprint class) and can burn to ~0%: solve
from a clean proxy LANE and submit through that same lane — local-IP solves get rejected while
same-proxy solve+submit passes. Rejects are retryable, so pace and rotate the solving class, and
never treat "the browser produced a token" as "the server accepted it". Full recipe:
`references/captcha-solver-farm.md`.

