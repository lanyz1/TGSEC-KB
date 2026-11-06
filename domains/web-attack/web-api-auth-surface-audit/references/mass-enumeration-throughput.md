# Running a mass-extraction campaign across multiple egresses

Depth behind R13. Applies whenever you are enumerating a sequential ID space or dumping records at a rate the
target's per-IP limit will not allow from one address.

## Egress matrix

| Egress | Sustained rate | Ban behaviour | Best use |
|---|---|---|---|
| Local SOCKS/Tor circuits (per process) | ~0.6 req/s | near-zero bans; circuits die and must be replaced | bulk scanning, run 6–10 bands in parallel |
| VPS / jump host, direct | ~2.4 req/s | 429s after a burst; recovers only after ~10 min cooldown | fast bulk scanning **and** interactive oracle probes |
| Rotating proxy pool | varies | shared reputation — one noisy user burns the pool | last resort; verify with a canary request first |

Rules of thumb:
- Total throughput ≈ sum of egress rates, so add egresses rather than raising per-egress concurrency past the
  point where 429s start.
- Reserve one egress for interactive work (schema tuning, oracle probes). Scanners stay off it.
- Retire a band when its hit rate collapses; stop it and start a denser band from the gap list instead.

## Jump-host operation

- Password-only host, no key: `sshpass -p '<pw>' ssh -o UserKnownHostsFile=<dir>/known_hosts \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no root@<ip> '<cmd>'`. Save the host key into
  the engagement dir on first connect; verify auth mode before assuming a key install worked
  (`PubkeyAuthentication no` is common on leased boxes).
- Launch long scans **detached**: `setsid /path/venv/bin/python3 -u /path/script.py > /path/logs/x.out 2>&1 <
  /dev/null &`. Plain `nohup ... &` looks alive immediately after launch and is gone by the next check — the
  SSH session reaps it.
- Absolute paths only inside detached scripts (cwd is not what you assume under `setsid`), and push the shared
  helper module to the host with `sys.path.insert(0, ...)` fixed on the remote side.
- After a concurrency burst 429s the host, cool it >10 minutes, then relaunch single-threaded and ramp
  gradually. Re-running the same burst immediately just re-arms the limit.
- To pull results back: `scp` the remote JSONL, then merge locally with the same dedupe path used for local
  bands, so remote and local captures cannot diverge in schema.

## Starting and stopping scanners without killing yourself

- `pkill -f '<pat>'` and `pgrep -f '<pat>' | kill` **match the invoking shell's own command line** whenever
  that line contains the pattern, so the control command SIGTERMs itself (`exit_code -15`) and the scanner is
  never touched — then you "confirm" it is still running and conclude the restart failed. Select PIDs
  explicitly instead: `ps -eo pid,args | awk '/<pat>/ && !/awk/ {print $1}'` then `kill <pids>`, or write `$!`
  to a `.pid` file at launch and `kill "$(cat x.pid)"`.
- Verify the survivor set after **every** start/stop: `ps -eo args | grep -c '[s]cript.py'` (the `[s]` bracket
  trick keeps the grep out of its own match). A control step that matched nothing silently leaves two copies
  appending to the same dump file.

## Merge and deliverables

- One append-only JSONL per entity type under `<engagement>/dump/`; dedupe/merge/count **in code**, never by
  hand. Emit flat CSVs for the user (`users_pii.csv`, `devices.csv`, `wallets.csv`, ...) plus the raw
  `users.jsonl` in the loot dir.
- Give each scanner a progress line (`prog <done>/<target> hit=<n> miss=<n>`) and grep the tail of every band
  when you poll — a silently stalled band looks exactly like a slow one.
- **Match the print cadence to the actual rate.** A `prog` every 300 completions at 0.35 req/s prints nothing
  for ~15 minutes, and a healthy scanner then looks identical to a hung one — you "diagnose" it, relaunch it,
  and stack duplicate processes on the same dump file. Print every 25–50 for sub-1 req/s scanners, and print
  the target count with the pace at startup so the silence is provably expected rather than suspicious.
- Poll on a bounded cadence: a single foreground wait long enough to exceed the command timeout loses the
  window and returns nothing. Use several shorter waits, or run the scan as a tracked background process.
- Report shape: counts table → file paths → blocking matrix. For every exhausted lever give the endpoint, the
  exact observed error, and the mechanism. An honest "blocked, here is the full evidence" beats a speculative
  finding, and a lever is retired only once its failure is recorded with a number.
