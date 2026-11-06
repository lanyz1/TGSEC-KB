# safe-bulk-cleanup — 全文续篇

> 主卡保留前 1 节；本文件从第 2 节起。原文件：`/root/.hermes/skills/devops/safe-bulk-cleanup/SKILL.md`

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

## Git repo bloat — the one case where deleting frees NOTHING

Trigger: 「仓库太大」「有什么大文件用不到可以删」「GitHub 仓库 290MB」.

**The trap.** `git rm` + commit + push does **not** shrink the repo. GitHub's reported size ≈ the local pack; every "deleted" blob is still reachable from history, so `size-pack` and the GitHub sidebar are byte-identical afterwards. Reporting "freed 280 MB" off a plain commit is a **false receipt**. Real reclaim needs a history rewrite: `git filter-repo --invert-paths` → `reflog expire --expire=now --all` + `gc --prune=now` → **force push** (rewrites every commit SHA; clones must re-clone).

**Measure, never estimate.** Copy the repo and actually run the rewrite — ~30 s on a 300 MB repo, and the copy doubles as a validated, push-ready artifact:
```bash
cp -a repo /tmp/repo-test && cd /tmp/repo-test
git count-objects -vH | grep size-pack    # BEFORE
uv tool install git-filter-repo           # uv, not pip (see Pitfalls)
git filter-repo --force --invert-paths --paths-from-file /root/cases/delete_list.txt
git count-objects -vH                     # AFTER
```
Byte-sum estimating is wrong in **both** directions: PDF/zip/jpg are already compressed (≈1:1 in the pack) while text/csv/json compress 3–4×. Only the measured pair is a receipt.

**Inventory** (`scripts/git_repo_audit.py` does all of it):
- HEAD-tracked sizes: `git ls-tree -r -l HEAD`.
- **Same-SHA blobs at many paths = mirror dirs** (`.agents/.claude/.codex/.cursor/.gemini/…`). They bloat the checkout but save ≈0 pack bytes — git already stores one copy. Fine to delete, but never book them as pack savings.
- **History-only blobs** (reachable from `rev-list --objects --all`, absent from HEAD) look innocent in `ls-tree` yet still hold the pack open. These are the "I already deleted that" files only a rewrite can clear.
- Categorise by extension to find the real fat: pdf / archive / binary / media / wordlist / data.

**Hunt derived artifacts sitting next to their source** — usually the single biggest win. Here: 628 wiki-scraped PDFs = 138 MB, each with a same-stem `.md` twin totalling 1.2 MB. Never delete on the filename pattern alone; prove the twin carries the content (below), then keep only the handful with **no** twin.

**Verify redundancy statistically before deleting at scale.** Sample 15–20 pairs, extract both sides' text, compare token + CJK-char overlap, and report the distribution (not one anecdote). Near-1.0 across the sample with zero empty stubs ⇒ the derivative is safe to drop. Raw-text extraction on this box: `uv venv /tmp/pdfvenv && uv pip install --python /tmp/pdfvenv/bin/python pypdf`. Recipe + code in `references/git-repo-size-audit-20261002.md`.

## Delivery + follow-through

Report table per group, the **measured** before/after, the exact reproducible command, a `.gitignore` hardening block, and a Tier-2 "what's still big" list. Keep the delete list on disk so the push is one command later. When the same conversation then says 「直接帮我优化好啊 然后推送到仓库」, that is the owner's yes **and** the execution order: land what's already approved, then use the remaining turn to ship the anti-recurrence layer (`.gitignore` + CI gate) as a normal commit on the freshly rewritten history — tested locally first (`bash scripts/check-large-files.sh`), tuned until it exits 0, then `git add` + `git push` (normal push, no force needed on top of the rewrite). First gate cut false-Failed 13 PoC binaries; iterating the whitelist until PASS is part of the delivery, not an extra round-trip.

**Execution — list first, then act on one word.** Present the groups and stop: a force push rewrites public history, so the owner's yes is required exactly **once**. When it arrives (「删除」/「用不到就删除」, or approval of only a later tier such as 「媒体用不到就删除啊」) run the whole remaining chain in that same pass — backup → rewrite → gc → force push → read-back verify — and do **not** ask again. "Delete" means delete; re-confirming is the behaviour this user pushes back on.

**Tier approvals are incremental, and a second pass is cheap.** A later yes for another group is just another `filter-repo` pass on the already-rewritten repo — 1.85 s versus 24.87 s for pass 1 — with `reflog expire` + `gc` run **only after the last** pass. Pass 1 took `291.08 → 88.67 MiB`; the Tier-2 media pass took `88.67 → 52.17 MiB` (−82% total). Use `scripts/git_history_rewrite.sh`, which encodes the whole chain including the backup and the keep-list assertions.

## Aggressive defaults (user:「清理干净 没有用的」/ 清盘默认激进)
When disk panic or explicit cleanup with no keep-list debate:
**盘面 ≥95% 先放血再精修**：截断 `/var/log/{syslog,auth.log,btmp}`（`: >`）+ journal vacuum + apt/snapd 缓存（零争议，一波常 −GB）→ 旧清扫归档 tar（junk-of-junk，留 manifest 与留存的 cron 文件）→ 活跃 IDE 日志 `truncate` 不删 → 才轮到案卷精修（每删一份先验重复：comm 子集 / md5 全等）。每波 `df -h /` 报数；完整配方：`references/disk-full-emergency-20261015.md`。
1. **Cron remove ALL campaign jobs first** (pause ≠ stop; 「停止所有」= remove + kill + confirm count=0).
2. Kill attack PIDs via `/proc` scanner (never `pkill -f`).
3. ARCHIVE then DELETE retired `/root/cases/<old>` workspaces.
4. **Trim current campaign bulky intermediates** without deleting deliverables:
   - DELETE: `loot/R*` round dumps, `recon/*.log`, `*_state.txt`, rockyou slices, LFI HTML noise
   - KEEP: `loot/FULL_USERS_PARTIAL.{json,csv}`, `REPORT-*.md`, FINDING_*, small key scripts, `campaign/`
5. Browser/runtime caches that routinely reclaim GBs (safe if no open handles):
   - **`/root/.trae-server/manager-logs/`** — Trae / VSCode-remote IDE logs, one dir per IDE session. Held **2.5G** on 2026-09-25 (single `ai-agent_*_stdout.log` was 815M). **Keep the session dir named in the live process cmdline** (`ps -eo pid,cmd | grep trae` → `--logsPath <dir>`); delete every other session dir.
   - `/tmp/snap-private-tmp/snap.chromium/tmp/` (~2.2G — see Pitfalls; verify no chromium proc + 0 cwd handles)
   - `/root/.cache/ms-playwright` (~1.3G)
   - `/root/.cache/camoufox` (~1.3G)
   - `/root/.cache/google-chrome-for-testing-headless`, `/root/chrome`, tmp playwright profiles
   - Do **not** auto-wipe `/root/.cache/uv` or nuclei/SecLists — tooling.
6. Optional: `journalctl --vacuum-size=50M`.
7. Leave gateway / mysqld / tor / `.hermes-botA|botB` alone unless ordered.
8. Receipt: MEDIA the manifest; report before/after `df -h /`, cron=0, attack procs=0, keep-list intact.
9. **Max pass — the tier to run when the user pushes 「还能清理更多吗」/「都清理好了没有啊」.** Never say "nothing left" before this: ① old-kernel family purge — **simulation gate first**: `apt-get -s purge -y <linux-*-<oldver> pkgs>` and require `grep '^Remv' sim | grep -vE '<oldver>|libxnvctrl0'` to be **0 lines** (any hit = meta-packages/deps would go too → skip); then `purge` → `autoremove -y` → `apt-get clean`. ② leftover installer zips in tool dirs (`clt.zip` 147M inside the Android SDK). ③ rebuildable caches: `/root/.cache/{hashcat,pocl}`, venv `__pycache__`, hermes rotated `logs/*.log.{1,2,3}` + `cache/terminal-output` files >3d. ④ `uv cache clean` — but `~/.local/share/uv/{python,tools}` (~630M: browser-use/pwntools/frida-tools/sqlmap) is **tooling, never wipe**. ⑤ close with the full-disk proof `find / -xdev -type f -size +300M -exec du -h {} + | sort -h` and label every survivor **gated-ask / owned-elsewhere / system-live** — that table IS the answer to "还能更多吗". This tier took 5.3G→6.1G.

## Pitfalls (all observed in the field)
- `pkill -f` self-kill (exit -15): see Step 0. The only safe path is the /proc scanner.
- `mysqladmin --socket=... ping` without credentials prints `Access denied for user` — that's a LIVE server refusing auth, not a down server. Verify liveness via `pgrep -a mysqld` + `ss -tlnp | grep 3306`. Don't chase the false alarm.
- **A process you cannot attribute is not a process you may kill.** Three `hermes_cli.main gateway run` processes look identical; one is yours, two belong to other profiles. The same ambiguity applies to shared infrastructure (tor, nginx, mysqld, 宝塔). Report it as "left running (not attributable)" instead of guessing.
- **Verify with `ss -ltn`, not with the kill's exit code.** A killed PID can leave the port held by a child/`crashpad_handler`; the port list is the ground truth for "released".
- Killing long-lived chromium under a *snap* install leaves `crashpad_handler` + zygote strays that keep the profile dir locked; re-scan the profile path after the kill before declaring it clean (and before deleting that dir as a bulk item).
- Live sockets/dirs never in scope: `/tmp/*.sock`, `systemd-private-*`, and the **`snap.*` socket dirs** directly under `/tmp/snap-private-tmp/`. But do NOT blanket-skip that parent — see next bullet.
- **`/tmp/snap-private-tmp/snap.chromium/tmp/` is a top reclaim target, not a protected dir.** It accumulates one dead chrome profile per browser launch (`rNNNp_PID`, `rNNN_chrome_PID`). On 2026-09-25: **249 dirs / 2.2G**. Reclaimable once BOTH checks pass: `ps -eo pid,cmd | grep -i chromium` is empty AND `ls -l /proc/[0-9]*/cwd 2>/dev/null | grep -c snap.chromium` == 0. Keep `*_profile` and any `*keep*` dirs. This alone took the box 89%→82%.
- **`find -name` glob must match the real name shape — group first, then delete.** `ls -d r* | sed 's/[0-9]\+/N/g' | sort | uniq -c` prints the shape histogram. My first pattern `r*_p_[0-9]*` matched 0 of 249 dirs because the real shape is `r359p_37121` (**no underscore before `p`**); it freed 434M instead of 2.2G. Never run a guessed glob — print the histogram and confirm the count/bytes before deleting.
- Hermes profile dir junk: `state.db.corrupt_*` → deletable; `state.db.bak.sessionclear` → keep (history backup); `*.lock` (0B) → leave; request dumps → leave.
- Big ≠ junk, and big ≠ deletable: 2.5G wordlists = tooling (keep); 2.8G ingest staging = absorbed (delete); 2.2G source dump = re-fetchable (delete, but archive its audit scripts/READMEs first).
- Playwright/Camoufox caches are usually the biggest reclaim on this box after campaigns; inventory `/root/.cache/*` early.
- Force-copy oversized deliverables (e.g. `FULL_USERS_PARTIAL.json` >256K) outside the archive size cap — don't rely on the generic ≤256K filter alone.
- When the user was shown a candidate list in your report and replies 「都删除」, that authorizes exactly that list (+ obvious trash discovered); keep small safety artifacts and disclose rather than deciding silently.
- **「全部都清」 after a per-case inventory is a scope escalation, not a request to repeat the inventory.** The prior "others untouched" stance is suspended **only** by that explicit whole-root confirmation. Confirm the exact path/contents once; then delete the whole root and report the cross-tenant impact plainly. Do not ask a second time, and do not quietly delete only your own cases.
- **The unit of deletion must be the named root.** `/root/cases` being purged does not authorize `/root/.hermes`, toolchains, `.cache`, models, or `case_*` siblings outside it. Conversely, `rm -rf /root/cases/*` can miss dotdirs and is harder to audit than `rm -rf -- /root/cases`.
- **Preflight cwd/cron scan is not a process-kill order.** `全部都清` is about files; if a cwd hit belongs to another bot, report it instead of killing an unattributable process. Data-dependent bots can error after their tree disappears — that is expected, not a reason to touch their PIDs.
- User expectation on pause/switch: land the report + send the file via MEDIA *before* finishing — receipts matter.
- **`git ls-tree` octal-escapes non-ASCII paths.** `git ls-tree -r -l HEAD` returns `…/\345\276\256\344\277\241.pdf`; `.strip('"')` leaves the escapes in place and every downstream `Path` / `PdfReader` call dies with `No such file or directory` (cost an entire 20-sample verification run). Always `git -c core.quotePath=false ls-tree …` when paths may be CJK.
- **Dedup-by-SHA accounting silently undercounts file totals.** Skipping already-seen blob SHAs is right for *pack* savings but wrong for a *file* count — mirror dirs reported 759 files instead of the actual 1,209. Cross-check every per-group count against the measured delta (files before − after); a mismatch means one of the two is wrong.
- **Gap-free filters only.** `(^|/)assets?/.*\.(gif|png|jpg)$` silently misses media that isn't under `assets/` (`…/CVE-2026-21508/alps.jpg`, `…/ios-vphone/vphone-aio/preview.png`, `…/centreon/…/command.gif`). After the run, re-list the biggest *remaining* files and present them as Tier 2 instead of declaring the job finished.
- **`filter-repo` strips the `origin` remote** — `git remote add` again before pushing. It also refuses a repo that still has a remote unless `--force`.
- **Re-verify the keep-list survived the rewrite.** `git ls-files | grep <pattern>` for every file you deliberately spared. A keep-list path typo (the file actually sits one directory up) silently deletes the thing you promised to preserve — caught only by checking, not by assuming.
- **Don't trust `head`/`tail` on a size-sorted dump of CJK paths** — it's unreadable. Sort by size but print the real path via `core.quotePath=false`, and write the raw list to a file for the report.
- **GitHub's API `size` field lags the rewrite — that is NOT a failure signal.** Minutes after a verified force push, `api.github.com/repos/<o>/<r>` still reported the old `297,322 KB` while a fresh `git clone --depth 1` showed a 56 MB `.git` with every deleted path gone. Never call the rewrite failed (or "still pending") off that field — but never call it succeeded off the push's exit code either. The fresh shallow clone is the only receipt. Old SHAs also stay dangling/reachable on GitHub for a while; say so, and tell every clone / CI / other profile to **re-clone** rather than `git pull` (which will conflict).
- **Put the keep-list assertions inside the delete-list generator, not just in your head.** `assert not any("panda-dex-dumper" in p for p in dead)` / `assert not any("payloader" in p for p in dead)` turn "delete every raster image repo-wide" from a judgement call into a crash-if-wrong gate: the script refuses to emit a list that would eat the tooling, instead of surfacing the loss after an irreversible rewrite. Pair it with a post-rewrite echo of the kept counts.
- **Re-run the inventory on the *filtered* repo to build the next tier.** After pass 1, list the biggest remaining files and present them as Tier 2 rather than declaring victory — that is how the media pass surfaced (118 images/videos the `assets/`-anchored regex had missed).
- **Hash-slug dirs can be THE main case — verdict by content, not name.** `drfmud7h5b2n` looked like scratch; it was the main active case (delivery zips + project notes inside). Read `NOTES.md` mtime, `deliver/` presence, closeout reports. When crons are already silenced, `stop_sweep/cron.d_disabled/*` is the ownership index for whose gear is whose (read `tato-emu` → `zhitian.jtxlhs.com/recon/tato_*` → the 9.2G stack stayed).
- **Every deleted copy needs deterministic proof:** set containment via `sort` + `comm` (delete only when the minority side is 0 — invite v1's 626k rows fully ⊂ v2, `v1_only=0`); dir-vs-zip via python `zipfile` + md5 of every member (6/6 equal → dir removed). For a CLOSED case's raw `.jsonl`, prefer **gzip -9 in place** over delete — path/name survive, 785M → ~100M.
- **Quote no number you have not read from a file.** Multi-section probe output truncated inline got misread twice (swap 3G as "8G", RAM 8G as "251G") → false "6G reclaimable" claim, corrected mid-task. `probe.sh > file` then `read_file` before quoting; truncated/regrowing logs judged by `du`, not `ls`; swapfile size via `swapon --show` before any shrink.
- **Truncated active log re-grows as a sparse ghost — expect it, don't fight it.** The writer keeps its file offset, so after `truncate` the apparent size climbs back toward its old GiB value while almost no blocks are allocated (`ls -l` 347M vs `du -h` 880K→1.8M, same file later same day). Verify `du -h` + `fuser -v <path>` (expect only the known writer, zero readers) and leave it; never loop-truncate. When the user pings about it, answer 'ghost size — real occupancy is KB' with the du/fuser receipts.
- **User ping 「？？」 right after a cleanup = show state, now.** Answer with one live probe batch (`df -h /; free -h; uptime; systemctl is-active …; residual-proc ps`) plus plain-language notes on anything odd (ghost sizes, intentional swap) — not narrative prose.
- **`kill` is not a stop for a `systemd` unit.** If a port reappears after the PIDs are killed, check `systemctl is-enabled`; `warp-svc`/`tor` respawned on `9050`/`40000` this way. Use `systemctl disable --now` only for campaign-started units; for pre-existing services stop and record the enable-state change. Verify `is-active` + `is-enabled` + `ss`, not just `pgrep`.
- **A PID/port/cron count is not the whole answer to 「都清理干净了吗」.** Split local runtime from target-side residue (test account with no delete route, overwritten field with no original, uploaded file with no delete API). Name exact identifiers; never answer “all clean” off an empty process list.
- **Bulk redaction can destroy the case.** A domain/password-candidate collision turned every `hutaocards` into `[REDACTED]`; use context-specific replacements and verify URLs/titles after.
- **Before proposing VACUUM/repack of a big SQLite DB, read the freelist.** `PRAGMA freelist_count` vs `page_count` on the live `state.db`: freelist≈0 ⇒ the file is all live rows, vacuum reclaims nothing — the only lever is a content decision (drop old sessions); say that plainly instead of implying a mechanical shrink.

## Files
- `references/cleanup-verification.md` — seven-layer post-stop verification matrix: systemd respawn, credential redaction, target-residue register
- `references/three-plane-teardown-20261019.md` — local host / target-side / agent `state.db` teardown: WARP mask repair, deleted-case-vs-surviving-ID-29 split, schema probe
- `scripts/scan_procs.py` — kill-safe /proc process finder
- `references/post-teardown-disk-cleanup-20261021.md` — reports-only retention + second-pass loose-file sweep; 2.3G archive + 686M `/tmp` staging deleted, 7.1G→10.4G
- `references/case-root-purge-20261021.md` — whole `/root/cases` purge after explicit 全部都清: one scope confirmation, 95,077-file preflight, 12G delete, 75%→51%, audit outside the deleted tree
- `scripts/roots_purge_preflight.sh` — read-only preflight for a case root: sizes, file count, top-level inventory, `/proc` cwd hits, cron/path references
- `templates/cleanup_two_phase.py` — archive→verify→delete script with manifest
- `references/workstation-2026-09-cleanup.md` — box layout, keep-list, archive conventions, 2026-09-11 deep-clean run log
- `references/stop-all-and-aggressive-cleanup-20260917.md` — cron-before-kill + aggressive archive/delete defaults from 2026-09-17
- `references/aggressive-cleanup-20260920.md` — 712win3 stop+trim + Playwright/Camoufox reclaim (~3G) run log
- `references/campaign-teardown-20260927.md` — close-out of a multi-week gambling-platform campaign: browser/tunnel/cron teardown, handoff-receipt convention, confirmed-vs-disproven ledger
- `references/shared-agent-host-deletion-scope.md` — multi-bot shared host: hot-zone cwd/fd map, 4-check ownership attribution, borrowed-key rule, retire-vs-keep verdicts, archive-then-delete retire protocol, state.db read-only pragma discipline (2026-10-10 full run: 93%→80%, 9 cases retired, zero other-bot impact)
- `references/git-repo-size-audit-20261002.md` — git repo bloat audit end-to-end: tracked/history/dup-blob inventory, PDF↔md twin statistical verification, two-tier measured filter-repo rewrite (291.08→52.17 MiB pack, 2,396 files), executed force push + fresh-clone read-back, .gitignore hardening
- `scripts/git_repo_audit.py` — re-runnable git repo bloat inventory: tracked sizes, same-SHA mirror dirs, history-only blobs, deletable-group rollup, measured vs estimated savings
- `scripts/git_history_rewrite.sh` — the execution half: dirty-check → timestamped backup → N `filter-repo` passes → `reflog expire`+`gc` → keep-list/size assertions, then (with `PUSH=1`) force push + `git ls-remote`/shallow-clone read-back
- `scripts/repo-poc-gate.sh` — copy into the target repo as `scripts/check-large-files.sh`: CI/pre-push gate, FAIL on demo media + duplicate skill mirrors, WARN on PoC weapon binaries (apk/exe/dll/zip are the payload, not junk — a naive >500KB gate false-Fails 13 of them and gets deleted by the repo owner)
- `references/disk-full-emergency-20261015.md` — disk-at-100% emergency on the shared multi-bot box (367M→6.1G over two passes): wave order, ownership forensics (`drfmud7h5b2n`=main case, `tato`=zhitian), comm/md5 verify-before-delete, gzip-in-place, swapfile shrink, old-kernel sim-gate purge, uv tools-vs-cache layout, sparse-ghost log, full-disk 300M+ survivor inventory, numbers discipline

