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

