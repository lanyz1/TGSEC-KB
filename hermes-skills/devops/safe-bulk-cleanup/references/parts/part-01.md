# safe-bulk-cleanup 全文 第 1/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## Workflow

### Step 0 — stop running tasks (when asked)
- **Cron FIRST, then processes.** `cronjob(action='list')` → remove/pause every campaign watchdog (`opensms_*`, `*_watch`, spray keepalives). Killing only the process is useless: no_agent watchdogs (e.g. `opensms_fast_watch.py` every 5m) will respawn `brute_breadth.py` and the user will ask 「为什么还没停止」.
- 「停止所有」 = remove ALL cron jobs (not just the noisy one) + kill attack procs + confirm `cronjob list` count=0 and `/proc` scan empty. Leave gateway/mysqld/tor/botA·botB alone unless explicitly ordered.
- Enumerate: process list, cron jobs, subagents. Kill by exact PID from `scripts/scan_procs.py`, one at a time (or batch those PIDs in a small Python killer).
- **Never `pkill -f <pattern>`** when the pattern appears in your own shell's command line — it SIGTERMs your own command (exit -15). Bracket tricks (`[a]b`) can fail too. Use `scripts/scan_procs.py <kw>` — reads /proc directly, never matches itself.
- Re-verify: rescan /proc (expect 0 hits), `cronjob list` empty of campaign jobs, listeners dropped (`ss -tlnp`).

### Step 0b — campaign switch (「清理打扫吧 切换目标了」)
Step 0 plus the campaign-specific runtime, in this order:
1. **Browser / CDP**: kill the chromium family for that profile dir, by PID (`ps -eo pid,args | awk '/t4chrome2/ && !/awk/ {print $1}'` → kill each), then confirm `ss -ltn | grep 9222` is empty. The renderer children are 20-40 PIDs; killing the parent takes them, but re-scan to be sure.
2. **Jump tunnels**: `ssh -N -D 0.0.0.0:1080 ... root@<jumpbox>` (and `-L` variants) are campaign artifacts. Match on the **key path in the cmdline** (`awk '/<keyfile>/ && !/awk/'`), kill the PID, confirm the port dropped.
3. **Listener/beacon ports** the campaign opened (XSS listeners, `python3 -m http.server 8899`, socat relays) — kill + confirm.
4. **Don't confuse system services with leftovers**: `:8888` = 宝塔面板 BT-Panel, `:3306` mysqld, `:80/:443` nginx, `:111` rpcbind, cupsd `:631`, tor `:9050/:9051/:8118`. Pre-existing ones stay — **but a service this campaign started/enabled is not a system service; it is a campaign artifact.** `kill` alone can be undone by `systemd`: check `systemctl is-enabled <unit>` and, for campaign-started units only, `systemctl disable --now <unit>`, then re-check `is-active`/`is-enabled` + `ss`. Observed: `warp-svc` and `tor` respawned on `9050`/`40000` after the PIDs were killed.
   - **`disable --now` is not final when the unit has `Restart=always`.** `warp-svc` came back `active/enabled` after a prior `disable --now`; `systemctl cat warp-svc` shows `Restart=always` and `WantedBy=multi-user.target`. For a campaign-started unit: explicit `kill <PID>` → `systemctl disable --now <unit>` → `systemctl mask <unit>`, then verify `is-active=inactive`, `is-enabled=masked`, and `ss` has no port (re-check after 3–5s). `mask` is reversible with `unmask`; record it. Only mask a unit this engagement started — never a pre-existing service the user needs.
   - **If `systemctl mask` does not persist, repair the unit link layer.** Observed `warp-svc` active again after `disable --now` + `mask`: `/etc/systemd/system/warp-svc.service` was absent but `/etc/systemd/system/multi-user.target.wants/warp-svc.service` still existed. Fix: stop/disable, `rm -f /etc/systemd/system/multi-user.target.wants/<unit>.service`, `ln -sf /dev/null /etc/systemd/system/<unit>.service`, `systemctl daemon-reload`, kill the explicit PID, then verify `is-active=inactive`, `is-enabled=masked`, `ls -l /etc/systemd/system/<unit>.service` → `/dev/null`, and `ss -lntp` has no port. Handle `tor` and `tor@default` separately; never mask a pre-existing service the owner needs.
5. **Gateways cannot be killed selectively** — every profile's gateway runs the byte-identical cmdline `python -m hermes_cli.main gateway run`, with **no profile name in argv** (profile is resolved from env/workdir). So `botA`/`botB` are un-matchable by pattern: leave all of them alone. Do not "clean up" an unexpected gateway you can't attribute.
6. **Write the handoff receipt into the case dir** (`交接单_已清理关闭.md`): what was killed, what was deliberately preserved, the case's confirmed high-risk findings, the **DISPROVEN** findings (so nobody re-walks them), and re-entry coordinates (still-working domains/endpoints) if it is ever reopened. Then flip the case to closed.
7. **Update persistent memory in the same pass** — mark the case closed and carry BOTH lists (confirmed vs disproven). This is the step that stops the next session re-digging a surface already known to be defended.
8. Stand by for the new coordinates. Do not ask which target is next.

### Step 0c — credential sanitation before closing a case

Run this **before** archiving or deleting a closed case's working tree. Probe scripts and reports are the usual leak:

```bash
CASE=/root/cases/<case>
grep -RInE 'Bearer [A-Za-z0-9._-]{20,}|password|passwd|secret|APP_KEY|BEGIN .*PRIVATE KEY' "$CASE" \
  --include='*.py' --include='*.sh' --include='*.md' --include='*.txt' --include='*.json' | head -50
find "$CASE" -type f \( -name '*token*' -o -name '*.pkl' -o -name '*.session' -o -name '*.key' \
  -o -name '*.pem' -o -name '*cookie*' \) -print
```

- Delete credential files; do not archive live tokens/cookies/PEMs. Reports keep `[REDACTED]`.
- **Never bulk-replace short strings that can also be identifiers.** A target domain that appeared in a password-candidate list was globally replaced; every report URL/title became `[REDACTED]`. Replace exact secret values or context patterns (`Bearer ...`, `password: ...`), preserve domains/product names, then verify headings/URLs.
- Probe scripts are not evidence by themselves: extract snippets into the report, then delete the closed case's `*.py`/`*.sh` (one case had 438) and count them in the receipt.
- Check `~/.bash_history` for inline tokens; remove only the offending lines, never truncate the whole history.
- Clean `/tmp` payloads/session files, `screen`/`tmux` sessions, and temporary `/etc/hosts` origin mappings too.

### Step 0d — target-side residue is a separate claim

`0 processes / 0 listeners / 0 cron jobs` proves **local** cleanliness only. After the stop order, deleting a test account or product is a **fresh production write**, not teardown. At most probe one documented route, then record:

```text
ID / identifier | type | attempted route | result | original captured? | action
users/29 R22 Tester | test account | DELETE /admin/users/29 | 405 | n/a | /edit 404; no UI delete -> residual
product 1 description | overwritten field | n/a | original not captured | no | set empty; irreversible
```

Close with two lines: **Local: 0/0/0 + units disabled + temp clean. Target: N residuals (why undeletable).** If the second line is non-empty, never say 「全干净」.

**If the owner answers 「都清理」/「连证据一起抹」 after seeing that split, treat it as explicit authorization for the deeper pass:** delete the case working tree/evidence/reports they just asked to erase (do not archive a copy they wanted gone), and attempt only the one documented target-side delete route. If the admin session is stale, try the canonical login once, then stop — never brute or guess routes. Record the residual and the auth/route reason; a `DELETE` 405 + `/edit` 404 + a login 302 means the account survives and the target side is not clean. (2026-10-19: 181M case dir deleted locally; `users/29` survived.)

### Step 0e — agent session history is a third plane (not target residue, not case files)

The case dir can be gone while the conversation store still holds the same secrets. Audit `~/.hermes/state.db` (2.4GB observed) before claiming local clean:

- The DB schema is version-dependent: **do not assume `messages.session_id` exists**. Run `PRAGMA table_info(messages)` and `PRAGMA table_info(sessions)` first; in one build `messages` has no `session_id` and the assumed query fails. Use the real session key from the schema.
- Read-only discovery first (`file:...?mode=ro`); search for target name, token, cookie, test email, and `[REDACTED]` values. Reports/case files may be deleted while tool-output rows still contain credentials.
- Purge only named closed/cron sessions, not the live session: `PRAGMA secure_delete=ON`, delete matching rows, then `PRAGMA wal_checkpoint(TRUNCATE)`. Never delete the active session from inside itself; use a separate process/session if the owner explicitly wants the whole transcript gone.
- A 2.4GB DB with `freelist_count ≈ 0` is all live rows; `VACUUM` will not shrink it. Purging needs a content decision, not a mechanical repack.
- If the owner only asked to delete case evidence, say the DB is agent history and is still present; do not silently equate “case dir deleted” with “conversation scrubbed”.

### Step 1 — inventory
- `du -sh /tmp/*/ | sort -rh` (+ same for working dirs) → sizes rank the targets.
- Dates: dirs via `ls -lad`; newest file inside via `find <d> -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %f\n' | sort -r | head`.
  - GNU find gotcha: `%T` must prefix EACH time component (`%TY-%Tm-%Td`). `%TY-%m-%d` silently expands `%m`/`%d` as mode/depth and prints garbage like `2026-644-1`.
- Name every unknown dir before touching it (peek top files / README / REPORT).

### Step 2 — triage & provenance (critical pass)
- **Open handles:** scan /proc cwd + fd symlinks for candidates (`ls -l /proc/[0-9]*/cwd 2>/dev/null | grep <pat>`; loop fds too). Any hit = keep.
- **Other agents/profiles sharing the box:** check their cron, processes.json, session stores. Read-only only — never modify another profile's files. Another profile's active material → keep.
- **Multi-bot shared host — hot-zone map FIRST:** `ls -l /proc/[0-9]*/cwd 2>/dev/null | grep -o "/root/cases/[^/]*" | sort | uniq -c | sort -rn` — any case dir with live processes = a running task (often another bot's) → 永不触碰. Then 4-check every retirement candidate: hot/fd scan → path refs in `/etc/cron.d/*` + `/root/.hermes/scripts/*` + cron jobs → `session_search` ownership → finality markers in its final report (完结封卷/FINAL = retire-able; 持续中/未拿/未拖 = keep). **Borrowed-key rule:** a cold case whose SSH keys are reread by another bot's running tunnel keepalive (`grep -rl <keypath> /root/cases/<other>/`) is off-limits even with zero cwd/fd hits. Full playbook + verdicts + retire protocol: `references/shared-agent-host-deletion-scope.md`.
- **Who wrote it & when:** Hermes profile `sessions/request_dump_*.json` timestamps reveal which session was live when dirs were written.
- Classify each item: DELETE (staging, caches, stale backups, absorbed source dumps) / ARCHIVE+DELETE (campaign workspaces with reports+creds+loot) / KEEP (tooling, infrastructure, user's active ops) / ASK (irreplaceable + ambiguous).

### Step 3 — build the script
Copy `templates/cleanup_two_phase.py`, fill the config lists. Archive small files under `<ARCH>/<label>/`, cap total size, log skips. Default mode = archive-only; `delete` arg = rmtree + full manifest.

### Step 4 — execute
1. `python3 cleanup.py` → verify archive counts, `test -f` key files (reports/creds) inside the archive.
2. `test -f <key1> && test -f <key2> && python3 cleanup.py delete` → expect 0 errors.
3. Post-checks: df, ls of cleared + kept dirs, leftover scan (e.g. `ls | grep -i corrupt`).

### Step 4b — post-teardown disk pass (「先清理磁盘」 after STOPPED)

A stopped case is not a clean disk. Treat 「删掉归档」/「先清理磁盘」 as a second, authorized pass:

1. **Extract the small evidence shell first** to `<case>_reports_<date>/`: `STOPPED.txt`, `TEARDOWN_*.md`, `MANIFEST.txt`, `SHA256SUMS.txt`; `chmod -R go-rwx`.
2. **Delete the bulk archive** (victim rows, APK/WGT/source extracts) only after that copy is readable. In the receipt keep two distinct pointers: `ARCHIVE:` = retained reports dir, `BULK_ARCHIVE:` = destroyed path + UTC time.
3. **Sweep loose files, not just dirs.** `du -sh /tmp/*/` misses regular files; a 686MB `/tmp/case_kdz_full.tgz` survived the first delete of a 2.3G archive. Run:
   `find /tmp -xdev -type f -size +100M -printf '%s %p\n' | sort -rn | head -20`
   `find /root -xdev -maxdepth 2 -type f \( -name '*.tgz' -o -name '*.tar*' -o -name '*.zip' \) -size +100M -print`
   Hash each hit (`sha256sum`) into the receipt, then delete.
4. **Clean only rebuildable caches** (`uv cache clean`, npm/apt/pocl/hashcat) and re-run `df -P /` + `df -h /`. Do not touch other cases, toolchains, or control listeners (`1080/2222`, system `3306/6379`).
5. **Close the receipt** with before/after available space + percent, freed total, retained size, 0 case processes/listeners, and the exact paths that are gone.

### Step 4c — whole case-root purge after an explicit 「全部都清」

Use this **only** when the owner has seen the per-case inventory and explicitly confirmed the whole root (e.g. "整个 `/root/cases` 12G 全删，包括别人的案卷"). Default shared-host behavior remains own-cases-only.

1. **One scope confirmation.** Present the exact path, total size, file count, and the fact that other operators' dirs are included; offer own-only / whole-root / keep-reports / cancel. After the answer, execute without re-confirming. The transcript's `clarify` choice is the authorization record.
2. **Read-only preflight** (`scripts/roots_purge_preflight.sh /root/cases`): `df -P /`, `du -sh`, top-level name/type list, file count, `/proc/*/cwd` hits, and cron/path references. A cwd hit means a running task owns that tree: stop **your own** task first; never kill an unattributed other-bot process. No hits ⇒ safe to unlink; open fds can delay space release, so compare freed bytes with `du` if needed.
3. **Manifest names, not payload.** Record top-level dirs + sizes + mtimes + file count in a TSV/TXT outside the tree. Do **not** hash 12G of victim data; hash only the small retained reports. The pre-delete manifest is the receipt.
4. **Delete exactly the named root**, not `/root` and not a glob: `rm -rf -- /root/cases`. Then `test ! -e /root/cases` (or `CASES_GONE`), `df -P /`, and a fresh `ls` to prove disappearance. 12G / 95,077 files completed in ~4 s; background only for millions of files or a slow disk.
5. **Audit lives outside the deleted tree**: `<case>_reports_<date>/TEARDOWN/CASES_PURGE_<date>/` with `README.txt`, pre-delete manifest, and delete log; `chmod 700` dir / `600` files. Never write the audit inside the root you are deleting.
6. **Report the whole truth**: before/after `df` and %, freed GiB, file count, dominant dirs (name + size), active cases that were included, and that no process was killed. Explicitly list what is outside the deleted root and therefore untouched (`.hermes`, tools/models, reports dirs, any `case_*` sibling). Do not claim "全干净" if outside dirs remain.

### Step 5 — report
Freed size + before/after disk %, archive location, explicit keep list, health checks. Attach the manifest (MEDIA). Then stand by — don't ask for new targets mid-flow; the user will give coordinates.

