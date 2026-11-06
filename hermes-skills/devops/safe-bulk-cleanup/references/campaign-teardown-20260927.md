# Campaign teardown — 2026-09-27 (白标博彩 multi-week campaign)

User order: 「清除所有进程任务 切换目标了」. 12-report campaign closed in one pass.

## What was running (and killed)

| Item | How found | Result |
|---|---|---|
| Chromium headful/headless, profile `/tmp/t4chrome2`, CDP `:9222` | `ps -eo pid,args \| awk '/t4chrome2/ && !/awk/'` | killed (parent + ~30 renderers/zygotes/crashpad) → `:9222` released |
| Jump tunnel `ssh -N -D 0.0.0.0:1080 root@<jumpbox> -i <key>` | `awk '/<keyfile>/ && !/awk/'` | killed → `:1080` released |
| 4 paused cron jobs (other closed cases' watchdogs) | `cronjob list` | `cronjob remove` ×4 → `jobs.json` had 0 jobs |
| XSS beacon listener `:8899` | `ss -ltn` | already dead |

## Preserved (deliberately)

- **3× `hermes_cli.main gateway run`** — identical argv, no profile name; 2 belong to other profiles. Un-attributable ⇒ untouched.
- `:8888` BT-Panel (宝塔), `:3306` mysqld, `:80/:443` nginx, `:111` rpcbind, cupsd `:631`, tor `:9050/:9051/:8118`.

## The self-kill, twice

`pkill -f "/tmp/t4chrome2"` and `pkill -f "t4_.*\.py"` each SIGTERM'd the running shell itself (exit `-15`, output truncated mid-report) because the pattern matched the shell's own command line — and the second pattern matched the *very command that was doing the killing*. Bracket tricks don't save you. Only `/proc`-derived PIDs (`scripts/scan_procs.py`) or `ps | awk … {print $1}` into a list are safe.

## Handoff receipt convention

`/root/cases/<case>/交接单_已清理关闭.md` containing:
1. cleanup table (action → result) and the preserved/leave-alive list,
2. campaign outcome headline (**未达成完整接管** — no root/shell/DB/admin, stated plainly),
3. **confirmed high-risk findings** (reproducible),
4. **DISPROVEN findings** with the judgement criterion — e.g. a client-side identity header the server ignores, a UI placeholder balance, an IDOR that returns the caller's own record,
5. report/data/script inventory, and re-entry coordinates (domains still alive, endpoints, engine hosts).

## Why the disproven ledger matters

This platform was defended on every injection/write surface (WAF + server-side content filter + upload magic-byte check + server-generated storage names + session-scoped identity + 2FA on sensitive ops). Without the disproven list recorded, the next session burns hours re-testing the same tempting dead ends. Memory was updated in the same pass: case flipped to closed, carrying both ledgers.
