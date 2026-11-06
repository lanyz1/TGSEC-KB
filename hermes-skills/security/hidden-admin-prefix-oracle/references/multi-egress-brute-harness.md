# Multi-Egress Brute Harness

Use when a single-egress brute is pinned at ~1–2 rps by per-IP rate limiting and you need orders-of-magnitude more.

## Decision order

1. Measure the single-IP ceiling first (30 threads, 100 requests). If it is ~1–5 rps with timeouts or 429s, threading is not your lever.
2. Check the host for extra egress: `ip -brief addr`, global IPv6 (`ip -6 addr show scope global`), additional IPs in the assigned block. A `/64` or spare IPs is the cheapest multiplier — bind the client to different source addresses.
3. No spare IPs → Tor multi-exit (§below). Requires `tor` installed and a working SOCKS port.
4. Public proxy pools are a last resort and a minutes-scale consumable — see the main SKILL.md.

## Tor multi-exit setup

One instance per `SocksPort`; the `ControlPort` is `SocksPort + 1` (used for `SIGNAL NEWNYM`). Config template: `templates/torrc-instance.conf`.

```bash
# per instance: DataDirectory must exist, be 0700, owned by the tor user
mkdir -p /var/lib/tor-instN && chown tor-user:tor-user /var/lib/tor-instN && chmod 700 /var/lib/tor-instN
cp templates/torrc-instance.conf /etc/tor/torrc-iN      # keep it readable by the tor user
chmod 644 /etc/tor/torrc-iN
su -s /bin/bash tor-user -c "tor -f /etc/tor/torrc-iN"   # check stderr for [err], do not assume success
```

Verify each endpoint actually exits from a **different IP** before trusting the fleet:

```bash
for p in 9050 9060 9070 9080 9090 9110; do
  echo -n "$p: "
  curl -s -m 12 -x socks5h://127.0.0.1:$p https://check.torproject.org/api/ip; echo
done
```

Force new circuits on rate-limit pressure:

```bash
printf 'AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT\r\n' | timeout 5 nc 127.0.0.1 <ControlPort>
```

## Runner architecture that survived contact

- **One process per shard**, 300–600 threads each (never >1000 in a single interpreter). Launch as `bash -c 'ulimit -n 65535; exec python3 -u runner.py …'`.
- **Circuit isolation per worker**: username in the SOCKS URL selects the circuit; distribute workers across instances by port. Reuse a session across many requests; rotate on failure, not per request (fresh circuits cost ~10x latency).
- **Global token bucket** gating every request (`RPS_LIMIT`), so the offered rate is tunable at runtime without touching thread counts.
- **Classification**: `404` → negative; `5xx` / 429 / challenge markers → push the candidate back and retry; anything else → suspect. Re-queue rather than tagging unverified candidates as done.
- **Confirmation**: probe a suspect from the direct path plus two other exits, and compare against a control prefix.
- **Resume state**: done-set in a JSON file written atomically (temp + `os.replace`) every few hundred verdicts; salvage a truncated file with `re.findall(r'"([0-9a-z]{1,8})"', raw)`.
- **Wordlist sharding**: split into disjoint files (`shard_i = candidates[i::N]`) and seed each shard's done-set from the union of every prior run's done-set, intersected with that shard. This lets several engines run in parallel without overlap and lets you re-point an engine at a fresh shard after a crash.

## Calibration numbers from one weak VPS (CF-fronted Laravel shop)

| Config | rps | Notes |
|---|---|---|
| direct, 30 threads | 1.5 | throttled via timeouts, no 429 |
| direct, h2 multiplexed, 100 concurrent | ~5 useful | 90% 429; the offered rate is meaningless |
| 1 Tor instance, 48 workers, isolated circuits | 48 | 0 errors |
| 6 instances × 20 circuits, 300 threads | ~22 per engine | 0 errors; multiplexing this hard per exit risks 429 |
| 6 instances, 900 workers, unique circuits | ~50 total | host Tor ceiling regardless of instance count |

Per-exit allowance was ~15–20 req/s before 429. The host Tor ceiling (~50–70 rps) — not thread count — sets the ETA.

## Ops checklist

- Confirm no auto-restarting `systemd` unit or timer is relaunching a brute before blaming your own configuration.
- After any `kill -STOP` cool-off, `kill -CONT` or use `kill -9`; SIGTERM is ignored while stopped.
- Put kill/restart sequences in a **script file**, not a one-liner that names the process pattern — otherwise the shell kills itself.
- Watch the target's own health while brute-forcing. After every rate change, probe `/` and `/products` (or two known-good pages) — if latency exceeds 5s or any returns 5xx, cut the rate. On a Hostinger shared host, 50 rps caused universal 502 + 12s page loads; 44 rps with a token bucket ran clean (0.4s pages, 0 errors). The correct rate is the one that produces zero 5xx, not the one the egress layer can push.
- **Rate ramp-up procedure**: start at 8 rps/engine (conservative), probe site health, step up by +7 rps, probe again, repeat until 5xx or >5s latency appears, then back off one step. This converged to ~22 rps/engine (44 total) on one target; a second pass pushed to 30 rps/engine (60 total) with 7.8s page loads (no 502) — usable but close to the edge. The sweet spot is the highest rate where `/` responds in <5s and 5xx rate stays at 0.
- **Use a restart script, not inline shell commands, for rate changes.** Write a `restart_runners.sh` that accepts the RPS limit as `$1`, kills old processes by bracketed pattern, updates the supervisor config, and relaunches everything. This avoids the repeated problem of `ps | grep pattern | kill` matching the invoking shell.
