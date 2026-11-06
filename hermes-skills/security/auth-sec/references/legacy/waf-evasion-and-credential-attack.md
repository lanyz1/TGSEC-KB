<!-- archived from /root/.hermes/skills/security/waf-evasion-and-credential-attack/SKILL.md on 2026-10-21 -->

---
name: waf-evasion-and-credential-attack
description: "Use when WAF or rate limits block API/credential attacks."
version: 1.1.0
tags: [pentest, waf, ratelimit, bruteforce, credential-attack, tor, redteam]
---

> 归档卡：原目录 `/root/.hermes/skills/security/waf-evasion-and-credential-attack`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/waf-evasion-and-credential-attack/…')`，不要相对 `references/legacy/` 解析。

# WAF evasion & credential-attack harness

Load this when an edge WAF, a CDN bot rule, or an application rate limit blocks API probing or
credential testing — or when a brute-force run finishes suspiciously fast, "hits" on an error
page, or the target account locks out after a handful of attempts.

## Precondition gate (standing user rule)

Credential spraying is a LAST resort, never an opening move. Do not start a spray unless the user
named it for this target, or the non-credential surface is exhausted (unauthorized access, IDOR,
business logic, JS-discovered APIs, session handling, side ports, injection).

- A captcha oracle, an enumeration oracle, or "no rate limit observed" does NOT license a spray;
it only lowers its cost. Priority is unchanged.
- Ten to twenty common passwords with no hit means the password policy is healthy. Stop and pivot
to logic/session surfaces; do not start a long background dictionary run.
- When the user says stop spraying: kill the running spray processes immediately, and state in the
report that common weak passwords were tested and spraying was stopped on request.
- Model the target's lockout/limit economics (§5) BEFORE committing to a dictionary. A run that
cannot finish inside the window is worse than no run: it costs hours and yields nothing.

## 0. Identify which layer blocked you — before choosing a bypass

| Response | Layer | Lever |
|---|---|---|
| HTML page branded SafeLine/Chaitin, 403 | edge WAF, **path rule** | **§6 path × ingress matrix first — the origin often serves it**; then §2 browser fetch |
| An edge (not app) block that survives every IP, method and cleared session | edge **path rule**, not a challenge | stop early and re-read the incident: an app-layer answer on the *same* path from another prefix/ingress is the real route |
| Cloudflare 1015 / 1010 / "Attention Required", siblings blocked too | Cloudflare per-IP rate/bot rule | rotate source IP (§3), cooldown |
| Cloudflare "Attention Required" on ONE path while siblings answer normally | Cloudflare **path rule** | do **not** rotate IPs and do **not** reach for the browser (§2) — it fires from every IP, every method and an already-cleared session. Record the path closed, then move to another ingress (§6) |
| Cloudflare **"Sorry, you have been blocked / You are unable to access <domain>"** for EVERY path, including paths that answered JSON minutes earlier | full-site **IP/ASN ban** on your egress | nothing on-host fixes it; switch egress class (§3b-3d). Expect hours, not minutes — a concurrency burst can convert a per-path rate limit into a multi-hour zone ban |
| A pooled egress class answers path A but returns the block page for path B, while another class shows the reverse | **per-(IP, path) burn** from your own traffic | the burn is per IP AND per path — never spend a fresh IP class on latency benchmarks against the path you plan to spray; keep an unbenched reserve per critical path (§3d) |
| JSON `{"code":429,"msg":"请求过于频繁"}` | application rate limit | more source IPs (§3) |
| **HTTP 200 with an EMPTY body / `application/octet-stream`** where the path answered JSON before | route-level **mute** (operator re-pointed/neutered the route mid-campaign) | test route **case variants** (`/api/User/` vs `/api/user/`) and diff against the client binary's endpoint set (§7) — one casing can be muted while the other still serves |
| JSON `登录失败次数过多` | application **account lockout** | §5 — stop, cooldown |
| **504 where sibling paths give 403** | **you are past the WAF**; edge proxied to a dead upstream | probe ops/relay entries (§6) |
| Custom 502/403 page with vendor footer link (`Protected By X`) echoing `client_ip`/`request_id` | branded commercial gateway (e.g. Peekabo), **path-literal rule** | not nginx/CF/SafeLine — bypass variants won't work; switch ingress (§6) and treat the path as UNKNOWN, not present |

- A path-blocked URL answers identically for every `Host:` value, `X-Forwarded-For`,
`X-Real-IP`, URL-encoding, dot-segment, matrix-param and HTTP-method variant. Confirm once, then
stop grinding bypass variants on that path — the rule is on the URL.
- One method sweep (GET/HEAD/OPTIONS/PUT/PATCH/DELETE) is still worth it: a `405 Method Not Allowed`
from the origin proves the route exists and that you reached the application.
- A `422` from a Pydantic/Swagger stack means parameters were validated before auth was checked.
It is NOT evidence about credentials — send `{}` and read the field names out of the errors.

## 1. Order of operations

1. Fingerprint the blocking layer (§0).
2. Recover the exact API contract from the client binary (§7) — every payload written before this
is a guess, and a single wrong field name makes every candidate fail identically.
3. Recover the client's hardcoded server list (§6) — alternate entries often have no WAF rule.
4. For a few path-blocked endpoints: browser in-page fetch (§2). Reconnaissance only.
5. For bulk work: source-IP rotation (§3) + a correct harness (§4) + the lockout model (§5).

## 2. A few blocked paths — browser in-page fetch

Load the real SPA, then issue the request from inside the page context. Same-origin absolute URLs
return real business responses because the request carries the browser fingerprint and any CDN
clearance cookies:

```python
new_tab("https://TARGET"); wait_for_load()      # navigate FIRST
js("""(async () => {
  const r = await fetch('https://TARGET/wuquan/userApi/userLogin', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({...})});
  return await r.text();
})()""")
```

Pitfalls:
- Navigate to the origin before reading `localStorage`/`sessionStorage` — on `about:blank` the eval
dies with a `SecurityError` and the whole batch is lost.
- Each eval has a ~5s budget: 5-6 requests per call, drive the loop from the harness. A long
in-page `sleep()` never returns.
- **The bypass is ephemeral.** After a few hundred calls the browser's own IP is flagged and
`fetch` starts returning the WAF HTML too. Use it to READ a handful of otherwise-blocked
endpoints, never as the brute-force transport. A fresh context/cooldown is the only reset.
- Relative URLs break when the tab is not on the origin — use the absolute same-origin URL.
- **Use the page's own stack to capture encrypted payloads and to finish gated form flows.** When a
register/login form works manually in the browser but your API-side reconstruction keeps stalling on
required fields, drive the browser instead of guessing: intercept `window.fetch` and
`XMLHttpRequest.prototype.send`, submit the form once with a KNOWN value, and read the exact request
body — that single submission settles the field names AND the crypto format you must re-implement
(§7). Then read `localStorage` for the session token it issued. One real submission ends a round of
blind field-guessing.
- **In-page fetch defeats a CHALLENGE, never a RULE.** If a path still returns the WAF block page from a
real browser session that is already sitting on the app — on every method — no amount of fingerprint
realism or cookie warm-up clears it, and the browser only adds risk because its IP gets flagged next.
Tell the two apart in one call: a challenge resolves itself after the JS runs, a rule returns the same
static block page immediately. A blocked path also proves nothing about the route's existence — a CF
rule matching a literal like `auth/login` fires whether or not the endpoint was ever configured, so
treating that 403 as "route exists, WAF-protected" aims the whole campaign at nothing.

## 2b. SafeLine (雷池/Chaitin) specific — measured behaviour

- It inspects **headers as well as bodies**: `authorize: ' OR 1=1-- -` gets the same 403 page as a
body payload. Do not assume header-injection is a WAF blind spot.
- It **decodes before matching**: `\u0027` JSON unicode escapes, `/**/` comment obfuscation and
case-mixing (`AnD SlEeP`) are all normalised and still blocked. Duplicate JSON keys are no help —
it parses the whole body, so the "WAF reads first key / app reads last" trick fails.
- **Chunked bodies are decoded too** — `Transfer-Encoding: chunked` does not slip past.
- **Body-size padding is not a bypass here**: it stops the 403, but anything ≥4KB turns into an
nginx `502 Bad Gateway` from the app/proxy body limit. Verify with a *benign* padded payload before
concluding a bypass — if benign 4KB also 502s, the limit is infrastructure, not a hole.
- A bare quote with no SQL keyword passes the WAF but returns the app's ordinary "not found".
**That is not evidence of SQL injection** — it only means no keyword matched. Do not chase it.
- **449/429 after high volume is a long-lived per-IP ban (tens of minutes).** Rotating to a Tor
SOCKS exit restores access immediately (`socks5h://127.0.0.1:9050`); keep the Tor path for the
rest of the session and pace at ≥2s.

## 3. Bulk — source-IP rotation by SOCKS credential isolation

### 3a. First try: `X-Forwarded-For` header rotation (cheapest)

Before spinning up Tor instances, test whether the app-layer rate limiter trusts `X-Forwarded-For`.
Chinese platform backends (Caddy/nginx + Go/Java) frequently key their per-IP counters on the XFF
header: rotating `X-Forwarded-For: 203.0.113.<n>` per request gives each request a fresh quota while
the real connection never changes.

- Measured this session: a login endpoint that had just served a 59-minute IP-ban notice accepted
`X-Forwarded-For: 203.0.113.x` rotation immediately — every request got a fresh quota window.
- Test in one call: trip the limit once (or read the limit string), then resend with a different XFF
value. If the response changes from the limit string to the normal auth response, XFF is trusted.
- Keep the fake space plausible (documentation range `203.0.113.0/24` or `198.51.100.0/24`) and pace
the requests anyway — the server-side account counter still exists.
- **XFF rotation has a ceiling — notice the moment it stops working.** The platform can run a
secondary real-IP counter behind the XFF-keyed one; when the block string (`当前网络已被限制…`)
starts persisting across *fresh* XFF values while the connection source is the only constant, XFF
is no longer the counter key. Stop minting fake IPs and switch to real exit rotation (§3b/§3c).
- If XFF is ignored, fall through to SOCKS isolation below.

### 3b. SOCKS credential isolation (when XFF fails or for raw throughput)

Tor isolates circuits per SOCKS username (`IsolateSOCKSAuth`): different credentials => different
exit IP => an independent rate-limit quota.

```python
px = {'http':  f'socks5h://{u}:{u}@127.0.0.1:9050',
      'https': f'socks5h://{u}:{u}@127.0.0.1:9050'}
```

- **Verify isolation on your port first**: fetch `https://api.ipify.org?format=json` through three
different credentials and confirm three distinct IPs. Some configurations silently reuse the
circuit, and you will wrongly conclude the limit is per-account when it was per-IP.
- Derive the random username from the word index so a retry of the same candidate is idempotent.
- Spin up extra instances with distinct `SocksPort`/`ControlPort`/`DataDirectory` torrc files.
New instances fail for the first ~30-60s while bootstrapping — those are connection errors, not
WAF blocks; verify connectivity before launching a run.
- Manual (non-systemd) extra instances have three edit-the-config fixes that otherwise surface as
bind/permission mysteries, not WAF problems: give every extra instance `--ControlPort 0` (the
default torrc re-declares `ControlPort 9051`, already held by instance one, and a listener bind
failure is FATAL); point `--DataDirectory` at a directory owned by the user tor ACTUALLY runs as
(service defaults like `User debian-tor` are read only from systemd's `--defaults-torrc`; a
hand-launched tor stays root and refuses another user's directory); and on AppArmor hosts keep data
dirs under the allowed prefix (`/var/lib/tor/**`) or relax the profile. Launch detached servers via
a small script file (setsid inside the script) — a manually launched tor dies with its parent shell.
- Measured effect: ~5/s (few shared exits, heavy 429) -> ~33-36/s (100 threads over ~36 instances).

### 3c. On-demand circuit rotation via the Tor control port (and two stall bugs to know)

When the box runs a numbered tor farm (`torrc-i1..iN`, each `SocksPort 127.0.0.1:9050+10n`,
`ControlPort +1`, `MaxCircuitDirtiness 120`, `NewCircuitPeriod 45`), rotate circuits on demand
instead of waiting for the timers:

- **`AUTHENTICATE ""` FIRST, then `SIGNAL NEWNYM`.** A bare `SIGNAL NEWNYM` answers
  `514 Authentication required` — which reads like an auth problem but is a protocol-order problem;
  even with `CookieAuthentication 0` the control connection must open with an empty AUTHENTICATE.
  Both commands then answer `250 OK`:
  `printf 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\n' | nc 127.0.0.1 <ctrlport>`. Confirm the exit
  actually changed via `curl --socks5-hostname ... https://api.ipify.org` before/after.
- **After NEWNYM, drop the connection.** An HTTP keep-alive session (`requests.Session`) keeps
talking through the OLD blocked circuit — the spray then "stalls": queue frozen, every request
answered with the block string, while manual fresh probes through the same port succeed. Use a
fresh session with `Connection: close` (or close the session) on every rotation.
- Rotate every ~5-8 sends and on every block sighting; requeue the blocked item with a retry cap
  (≈3) so a fully blocked farm cannot requeue-loop forever. Stall symptom to recognize: the done
  counter keeps climbing while the queue size stops shrinking.
- A blocked exit's countdown re-arms on each new failed attempt — never retry through an exit that
  just returned the block string; rotate first, then requeue.
- **Verify the live port set at run start (and after every farm restart).** Build the transport's
port list from the actual listeners — `ss -tlnp | grep -oE '127.0.0.1:9[0-9]{3}'` — never from the
assumed `9050+10n` sequence: an instance that failed to launch leaves a gap port whose SOCKS
connections fail instantly, and the empty responses then get misclassified downstream as "no answer
from the target", corrupting the retry funnel and the stats alike.

### 3d. Third tier: free HTTP proxy pools (your IP banned, Tor flagged)

When the origin/WAF bans your egress ASN zone-wide and Tor exits are challenged or blocked on the
paths you need, public HTTP proxies are a third, independent IP class that can pass a path your
server IP and Tor both fail — and vice versa. They carried a campaign after both other tiers died.

- Harvest from the aggregators: TheSpeedX/PROXY-List (`http.txt`), monosans/proxy-list
(http+socks), proxifly/free-proxy-list, clarketm/proxy-list, roosterkid/openproxylist, the
proxyscrape API, proxyspace. Thousands of candidates; expect low single-digit percent to reach the target.
- **Keep a live pool FILE and test against the exact path you will use.** Keep only proxies that
return the target's *business JSON* (positive match: body starts `{` and carries a success marker) —
a proxy that serves other sites but returns the WAF page here is dead for your purpose.
- Rotate one proxy per request with 2-3 retries across DIFFERENT proxies before classifying an
attempt as transport-error — a dead proxy must never consume a credential candidate or a queue slot.
- **Score the pool, don't draw it blind.** Keep a small state file per proxy (ok / fail counters,
last-used, last-ok) and select the oldest under-cooled proxy with the best net score; report every
result back. A random draw re-burns known-dead IPs; one good proxy reused at a bounded rate beats
ten random draws. Fake "responder" proxies return junk like a literal `ok` body — positive-match
classification (business JSON only) turns them into fails automatically.
- **Refresh the pool on a loop** (harvest → test → merge every ~30 min) rather than one harvest per
campaign; free pools turn over within minutes-to-hours. Cap parallelism per proxy (semaphore ~2):
free proxies collapse under parallel load long before any target-side limit, and the collapse reads
as transport errors, not blocks.
- Re-test and re-harvest periodically (free proxies decay within minutes-hours). Sizing is
latency-bound, not count-bound: individual proxies are slow (seconds/request), so run 10+ parallel
consumers and let pool breadth absorb it. A few dozen live proxies sustain low-tens of req/min.
- **Different egress classes get different WAF verdicts — use the split as your classifier.** Same
path, three sources: server IP blocked / Tor challenged / clean proxy answers → that was an
egress-class rule; keep rotating and use the class that passes. Blocked identically from clean
proxies AND real browsers AND fresh Tor circuits → genuine path rule (§0): stop rotating for that
path. Probe any disputed path from 2-3 independent egress classes before recording it closed.

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

## 5. Lockout vs rate limit — model both before a big run

- The **per-account** failure lockout threshold is small (order ~10). Once tripped it answers the
lockout string for that account regardless of source IP and **masks the real verdict** — a
wrong-password test that returns the lockout string is not evidence about the password.
- Whether a large run survives depends on the lockout being keyed per account **+ source** rather
than per account alone: spread attempts over many rotating exits and the per-source counter never
reaches the threshold (100k+ attempts completed against one account). Concentrate attempts on a
few reused exits and the same account locks after ~10.
- **Per-endpoint limits differ on the same host — measure each endpoint separately.** On one
platform the admin console login allowed only ~6 failures per exit before a 59-minute network
block, while the member app login on the same infrastructure sustained hundreds of attempts per
minute across rotating exits. The member-side login is often the softest credential oracle; test
both before sizing a run.
- **Shared credential store across surfaces = a free, precise role oracle.** When the admin console
accepts a *member* account's password and answers `insufficient authority` (rather than the
invalid-password string), the store is shared and the account merely lacks a role: classify `400`
wrong / `403` valid-no-role / `200` token. Sweep every cracked (account, password) pair against the
admin endpoint — role membership is the only remaining unknown.
- **Status-check order decides what a login response leaks.** Deployments that check account status
(frozen / banned) *before* verifying the password answer the ban string (`您的账户已禁用：<reason>`)
for ANY password. Consequences: (a) the string is a password-independent **existence oracle** — the
number is a real account; (b) it can never validate a password, so stop spending candidates on such
accounts; (c) forks diverge — a fork that stops normalizing leaks ban reasons the upstream hides
(upstream merges user-not-found / freeze / invalid-password into one invalid string), so test one
known account per class to learn the live fork's semantics.
- **A single pass is not a verdict.** Rate-limit and empty / transport responses are not negative
results: a single-pass sweep bucketed 241/250 pairs as "invalid", and re-testing showed the bucket
was overwhelmingly rate-limit noise (true negatives: single digits). Keep retrying every pair with
fresh exits until it returns a real verdict (hit / valid-no-role / explicit wrong-credentials)
before reporting any count.
- Therefore: **one account per harness run.** Never run a second spray, or a slow manual probe,
against an account already being sprayed — it poisons the first with lockout responses.
- A slow single-candidate probe is WORSE than the bulk harness here: fewer source IPs means the
lockout trips almost immediately and every candidate returns the masking string.
- Confirm the account is unlocked with a single probe after cooldown before resuming.
- **Measure the lockout on the SECOND FACTOR separately from the password step.** A login that
locks after ~10 wrong passwords frequently applies no counter at all to the TOTP/OTP field. Send
~10 wrong 6-digit codes and watch for a lockout string: if none appears, the second factor is
brute-forceable — space 1e6 with roughly 3 codes valid at any instant, so expect a hit near ~333k
attempts. Persist the scan index so a restart resumes; one hit is worth the hours because it
converts an already-known password into a live session. Never start this when the field does lock.
- **Password lock can still fire during a "TOTP-only" scan.** If the client resubmits
`username+password+code` on every attempt, the server may increment the **password** failure
counter (or a combined counter) and answer `密码错误过多锁定…分钟` even while wrong-code responses
stayed unlockable. On any password-lock / account-lock string: **kill the harness immediately**,
cooldown, single unlock probe, then resume from saved index — do not keep range workers up because
"TOTP had no lock". Prefer transports that only vary the MFA field when the API allows it.
- After MFA success, **do not run a second login-generating job** against the same account while
using the fresh token (single-session). Further failed logins plus noisy egress often graduate the
edge from rate-limit into a long CF/WAF hard-ban on the admin host; pivot the live token to weaker
origins first, treat re-auth as a new cool campaign.
- The second-factor scan is a *positive-match-only* run (§4) and MUST treat any non-"wrong code"
response as unknown-and-stop: the response that means success (a token) and the response that means
lockout look nothing like the failure string.

## 6. Client-side server list = alternate, often weaker, entry points

Decode the class that builds the client's base URL (`baseUrl(X.y())` -> storage getter -> a
hardcoded obfuscated literal) and decode the whole server list. Clients ship 3-6 entries: CDN
domain, one or more direct `IP:port` backends, and an ops/relay host.

- Probe every entry with the same route set. An alternate edge frequently has **no edge WAF rule**,
so administrative paths answer normally.
- **The rule sets differ *per path*, not per entry.** An origin is not simply "an edge with the rules
turned off": it applies its **own** blocklist. Expect a split — the edge blocks the whole business
surface while the origin serves it, and both block the token-minting/admin paths. So build a
**path × ingress matrix** (CDN domain; each origin `IP:port` over BOTH HTTP and HTTPS) against a
real recovered endpoint list, and classify every cell: WAF page / business JSON / `404` (route
reached the app) / timeout. Only a path blocked in **every** cell is genuinely closed.
- **Re-test blocked paths with a valid session header.** Some rules match the request *shape*, not
the URL: a path that returns the WAF page for an anonymous `{}` body answers normally once
`Authorization` and the app's own token header are set. Cheap — do it before writing a path off.
- **A resolved per-path edge rule is a standalone finding, not a nuisance.** It means the CDN's URL
rules are the de-facto access control for that surface. The campaign consequence outranks the bypass
itself: **every endpoint previously recorded as "blocked/closed" must be re-tested through the
origin**, because that verdict was only ever true at the edge.
- `404` = route not configured there; `504` = route configured but upstream dead. Both are useful
and distinguishable from the WAF 403 page.
- Resolve each entry's PTR: a dynamic residential ISP hostname marks operator infrastructure (a relay), not a CDN edge.
- **`--resolve` over Tor reaches origins that IP-whitelist their CDN.** `curl -sk --socks5-hostname 127.0.0.1:9050 --resolve domain:443:ORIGIN_IP https://domain/path` makes the origin see a whitelisted (CDN/Tor) source and answer directly. This shows responses the edge never gives: real nginx/Go 404 where the edge returned an SPA-fallback 200, and route-existence (308 redirect / raw framework 404) for paths the edge disguised. Use for path-existence probes — and treat any gateway block page from ONE ingress as unproven for the route.
- **Origin vhost matrix**: same IP with different `Host:` values (`www.domain`, bare `domain`, `admin.domain`, `api.domain`) splits services; combine with BOTH HTTP and HTTPS ports. 404 (nginx default server) vs 308 vs real app HTML tells you which vhost is which. The origin applies its own rules — a path blocked at the edge can answer from the origin and vice versa.
relay), not a CDN edge.

## 7. Recover the contract from the client binary before writing payloads

For Android targets, APK string de-obfuscation turns guessed field names into exact ones:

```python
KEYS = [61945, 41027, 37077, 65535]
def se_v1(s):  # s = the decoded Java string literal passed to _se_v1("...")
    return ''.join(chr(ord(c) ^ KEYS[i % 4]) for i, c in enumerate(s))
```

- Extract every `_se_v1("...")` literal, unescape Java escapes, then XOR. Decrypt the **whole
class set**, not just the login activity — the base URL, the signing config and the parameter
names live in different classes.
- Filter to printable codepoints before printing or the dump dies mid-scan on surrogate pairs.
- Highest-value outputs: the `addParams("…")` field names, the default server list (§6), and any
AES key/IV pair used for request encryption.
- **A client-side-encrypted field must be re-implemented from a CAPTURED request, and the padding is
the silent killer.** Verify against one real submission (browser interception, §2) before any spray:
on the same key/IV, zero-byte padding (`.ljust(16, b'\\x00')`) and PKCS7 produce different
ciphertexts, and the wrong one answers the ordinary invalid-password string for EVERY candidate — a
'0 hits' run is then not evidence of anything. Measured: PKCS7 logged in where zero-pad returned
INVALID_PASSWORD; re-testing the high-value candidates the broken engines had rejected produced ~10
confirmed hits, several of them chat-leaked credentials previously marked 'invalid'. After any such
fix, audit every spray engine (`grep -A3 'def enc' *.py`) and re-run the top candidates it rejected.

**Server side too — clone the admin framework when the panel is an open-source stack.** Chinese
admin panels (go-wind-admin and siblings) answer their auth questions faster from the repo than
from black-box probing: seed credentials (constants files — e.g. go-wind-admin currently seeds
`admin` / `Abcd@1234`, its older plain-`admin` default retired for failing the framework's own
complexity policy), the error-normalization map (which failure classes merge into one string — this
decides which oracles survive), rate-limit dimensions (IP vs IP+username — still re-measure on the
deployment), and password-policy size. Forks diverge from upstream, and the deployed front-end
bundle tells you which fork is actually live.

## 8. Depth notes

- `references/china-spa-im-api-contract-notes.md` — field-shape and oracle detail for Chinese
SPA + IM-overlay platforms: login oracle strings, setting maps that switch the auth mode,
OTP reset flow, mail-panel enumeration oracle, trusted-device replay, the **edge-vs-origin path
split** (which surface the origin serves that the edge blocks, plus its money/group contract
notes), and which endpoint classes stay blocked everywhere.
- `references/member-tree-harvest.md` — multi-level platform member-data expansion after a
takeover: measured weak-password pattern library for member/leader accounts, downline-tree pull
contract (incl. unmasked sibling-endpoint discovery), masked-phone unmasking by cross-reference,
and the recursive harvest loop.
- `references/captcha-solver-farm.md` — captcha-gated credential attacks: gate detection, solving
Aliyun-class captchas from a locally-hosted page with Playwright real-mouse drags, the solver-farm
file queue, one-solve-per-attempt consumer semantics, and volume-vs-acceptance behaviour.
