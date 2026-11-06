# safe-bulk-cleanup 全文 第 2/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

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

