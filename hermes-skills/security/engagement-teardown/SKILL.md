---
name: engagement-teardown
description: "Use when a pentest engagement ends: stop, clean up, switch."
version: 1.0.0
tags: [pentest, cleanup, teardown, hygiene]
---

# Engagement Teardown

Use when the user says 停止 / 取消 / 打扫清理 / 切换新目标 — end of an engagement. The deliverable is a **verified** clean
state plus an archive, reported as counts, not as a narrative.

## Procedure

1. **If the request pairs a report with the teardown (审计报告 / case report / 结案报告), write it FIRST** — before
   killing, archiving, or wiping. The report is a deliverable that belongs *inside* the archive, and it can only be
   written while the raw dumps and the analysis scripts are still in the working tree.
   - **Re-derive every number from the raw files, in this session** (`wc -l` the dumps, re-count rows, re-sum the money
     columns, re-count distinct identities) and print a fact sheet to paste from. Totals recalled from earlier turns
     drift; a report is only worth the figures that were re-measured. Reports where a summary line contradicted the
     detail lines are the tell that no facts pass ran.
   - **Deduplicate before any per-entity rollup.** One identity can sit in many rows — multi-group memberships, a leader
     present in every group they own, operator/CS accounts in hundreds — and summing a per-row metric over those edges
     multiplies the total (a balance rollup read ~2.7× the true figure this way). Count distinct identities or exclude
     the multi-membership accounts, and state the 口径 in the report (counted-by-record vs counted-by-distinct).
   - **Shape it for the client**: metadata + authorisation basis → executive summary → asset inventory → attack chain →
     findings table (severity + CWE) → data-exposure inventory with counts → impact → prioritised remediation (P0/P1/P2)
     → evidence index → read-only/compliance statement → limitations. State plainly what was NOT obtained and why.
2. **Kill the live processes.** Enumerate this engagement's scripts and listeners — the working dir's `*.py`, your
   callback/listener ports, any background spray/harvest job — and kill each one **by PID**.
   - **Do NOT reach for `pkill -f <keyword>`.** The pattern matches the shell running your own command line, so it
     SIGTERMs itself and the teardown stops half-done. Use explicit PIDs (`ps -eo pid,cmd` → filter → `kill`),
     `find … -delete`, or an exact process name.
   - **Kill the scheduling layer too, and delete the job rather than pausing it.** Sweep the job runner
     (`cronjob list` / `crontab -l` / systemd timers) for anything that keeps this engagement alive — payload
     re-plant, listener watchdog, harvest retry — and remove the job outright. A paused job is one resume away, and a
     self-heal loop restarts your listeners inside its own interval, so a "stopped" engagement quietly comes back.
   - Escalate per PID: `kill -TERM <pid>`, re-check, `kill -KILL` only for survivors.
3. **Verify zero.** `ps` shows no residual engagement process, `ss -lptn` shows no listener on your callback ports,
   and re-listing the job runner shows no engagement job.
   Report "0 processes / 0 listeners / 0 jobs" verbatim — that count **is** the evidence the user wants, not a prose
   claim. Check `ss` even when `ps` looks empty: a leftover listener is still an open door.
4. **Archive before deleting anything.** `/root/loot_archive/<target>_<YYYYMMDD>/` holding the report, the delivery
   the delivery pack, the full text/json loot, and `STOPPED.txt` (target, date, "do not resume without explicit re-authorisation").
   Package first, archive second, and **send the `MEDIA:` paths from the archive directory** — a path that pointed into the working tree dies the moment you `mv` it, so any later 补件/增量交付 must also be rebuilt and re-verified in place there.
5. **Wipe the working tree.** `find <workdir> -mindepth 1 -delete`, keeping the archive path intact. Then `cd /root`:
   deleting the session's current directory makes every later command fail with
   `getcwd: cannot access parent directories`.
6. **Record state.** Write the hard-stop, the archive path, and "do not resume without explicit re-authorisation" to
   memory, matching the convention already used for other stopped engagements.
   - **`memory` 的 replace 是「整条替换」不是「改子串」**：`old_text` 只用来**定位条目**，`content` 会**覆盖整条**内容。想给已有条目补一句话，也必须传**完整的新条目文本**；只传片段会把该条其余内容静默删光（实测一次就丢掉了整条目标档案）。写完回读确认条目仍完整。
7. **Switch targets by asking, not guessing.** After teardown, ask for the new target (domain/IP, scope, known starting
   point). Never pick the next target yourself.

## 磁盘腾挪（用户说「先清理磁盘啊 把没有用的都清掉」）

**这不只发生在收尾** —— 活跃期要跑大导出（线上全量重拉）时也会先要求腾空间。目标是**把空间还给当前交付物**，不是「清得越空越好」。

**先量后砍**：`df -h /` → `du -sh /root/* /root/.[a-z]* | sort -rh | head -30` → 只对可疑的大头再 `du -sh <dir>/*`。
**动手前先把工具链目录看清**（`tools/src` 里的 sqlmap/jadx/ghidra/SecLists 是吃饭家伙，别当垃圾扫掉）。

**可安全删（按收益排序）：**
- 包管理器缓存：`~/.cache/uv`（单个常十几 GB）、`~/.cache/pip`、`~/.cache/go-build`、`~/.npm`；Go 模块缓存 `~/go/pkg`、`~/gopath/pkg` —— 全部可重下。
- **已交付的重复包**：交付 zip + 分卷 + 逐表目录常把同一份数据存三遍。**留一份可重建的**（逐表 CSV 目录或 zip 任选其一，另一份分钟级就能重切/重压），其余删掉。
- 与本役无关的 IDE/构建服务残留、未使用的工具 venv、旧的 `state.db.bak.*`。
- 上一批（已交付/已停）目标的**中间产物**：APK、抓站 HTML、媒体样本、二次转存的 dump —— 留交付包 + 全量库即可。
- 老目标的原始 loot 舍不得删 → **压缩归档**（`tar` + `zstd`）而不是留着一堆散文件。

**绝不动**：当前目标的**全量库（sqlite/dump）+ 原始 dump**、交付包、报告/进度存档/复取脚本、工具链与技能库、`loot_archive/` 里的 STOPPED 归档。

**清完必须回验**（不验 = 可能把证据清了还在报喜）：
- 列一遍核心资产的存在与大小 → 打开 sqlite 数表数 + 数一张主表和一张关系表 → 跑一次复取脚本确认通道还活着 → `df -h` 报释放前后的数。
- 收尾回复给**释放总量 + 删掉的类别表 + 「一个都没动」的清单**，用户要的是这两个数，不是 bash 过程回放。
- **用具体路径 `rm -rf`，不要用会命中自己命令行的通配/关键词模式**（同收尾杀进程那条陷阱）。

## 解释后台 / 定时任务的通知（用户问「这个是什么意思啊」）

交付之后、乃至目标仍在活跃期，收尾时留下的采集/监控任务会自己往聊天里推报告，用户看到会以为攻击又动了。
**开头第一句必须先给「不是新攻击」**，然后按四拍讲，别从过程讲起：

1. **定位任务**：`cronjob_manage list` 找 job_id → 看它跑的是哪个脚本（相对路径默认落在 `~/.hermes/scripts/`）→ 读脚本，弄清它拉什么接口、写哪个文件/库、多久一次。脚本型（`no_agent`）任务的 stdout 就是它发给用户的正文，**0 新增时通常不发声**（只因另一路有增量才打印）——「新增 0 条」本身是「没动静」的证明，不是失败。
2. **每个数字都要 map 到它的存储**：`wc -l` 它写的文件、`SELECT COUNT(*)` 它写的库。**它报的「主库 N 用户」多半是某个侧库/增量库，不是你交付的那个主库** —— 先确认这一点再开口，否则一句「库变了」就变成假警报。报数**点名库文件名**（`..._v2.sqlite` 314,419 vs 侧库 `fund_all.db` 102,501），并说清侧库的来源渠道分布。
3. **报负载与进程**：每个周期发几个请求、是纯 GET 列表接口还是攻击型并发，并给出 `ps` 里相关 PID（含配套的常驻采集/滴灌进程）。
4. **给一个字的停法**：「留着」= 继续增量；「停掉」= 暂停该 job 并按 PID 杀掉配套进程，交付物不受影响。

## Pitfalls
- **排除法清扫目录时，`grep -E '^(A|B|C)$'` 的锚点作用于整串**：`systemd-private-`、`hermes_rpc_`、`safe-rm-source-flag-` 这类**前缀清单会全部失配**，系统件（服务私有目录、Hermes socket、sandbox 旗标）被当战利品搬进归档（实测误搬 19 件后修复）。用**无锚点子串匹配**或逐项 `[ -e ]` 试探，搬完对照系统件名单复核归位。
- Don't resume a stopped engagement because a stale background job prints a "completed" notification — that is a
  historical exit replay, not new work. Say so explicitly and re-state that the live-process count is zero; do not
  emit fresh attack progress after a stop order.
- Don't leave the analysis scripts sitting in the working tree "in case" — they go into the archive with the loot, never
  stay runnable in place. A stale script next to the target's data is what gets re-run against an engagement the user has
  already closed.
- Don't summarise the engagement as a victory lap during teardown. The user asked for a clean state; the count, the
  archive path, and the next-target question are the whole reply. (A report the user explicitly asked for is not a victory
  lap — send it as a file and keep the prose to the counts.)
- **Filter the process scan to THIS engagement** (working dir, your own script names, your callback ports). A broad `ps`
  also lists other cases' and other profiles' jobs — those are not yours to kill: name them as not-this-engagement and
  leave them running.
- **无头浏览器（headless Chrome/CDP）不在「脚本名/python」杀法里——单列一类扫杀。** 案用工具浏览器（`--remote-debugging-port=92xx --user-data-dir=/tmp/chrome-profN`）是独立进程树：按脚本模式清理时整窝漏网（实测 24 进程存活 26h、92xx 调试端口仍 LISTEN、profile 被删后 inode 悬空）。收尾判据两样：`ss -lptn` 看 92xx 端口 + `ls -l /proc/*/cwd | grep <案目录>`（进程 cwd 会随归档 `mv` 指进新路径，这是最快的占位证据；先排除自己 shell 的瞬态命中）。杀法：TERM 根进程 + crashpad/zygote/renderer 全 PID 列表，复查后 KILL 幸存。验证：端口 CLOSED、cwd-holder 零、`pgrep -c chrome` = 0。
- **删大目录前用 cwd-holder 当 guard**：`ls -l /proc/*/cwd | grep <目标目录>` 非空就先杀活口再 `rm -rf` —— 撞上持有者照样删得掉，但空间要等进程死才还，且对「案是否真停」是假阴性。
- Archiving is satisfied by one `mv` of the whole working tree into `/root/loot_archive/<target>_<YYYYMMDD>/` — the wipe
  then reduces to removing the emptied dir. Copying out only "the important files" drops the raw evidence a later report
  or re-verification needs. Keep `STOPPED.txt` (target, date, do-not-resume) at the archive root so the state is legible
  without reading any script.
- **A non-zero hit from your own teardown scan is usually your own shell.** Once the archive path exists, the command
  line running the scan contains the engagement keyword, so `ps | grep <keyword>` returns a line that is not a residual
  process — and bracketed patterns (`[x]ss_srv`) do not save you inside a `sh -c` wrapper whose full command text sits
  on the line. Print the matched PID + command (and exclude your own PID) before believing any non-zero count; never
  report residual processes you have not actually identified.
- **Record what you left on the target; do not clean it up after a stop order.** Planted payload rows/accounts, uploaded
  files and created sessions get listed by exact identifier in the report and in `STOPPED.txt` so the client can remove
  them. Removing them is itself a fresh write to a production system and needs explicit re-authorisation — leave them,
  and state in the closing reply that they are still there and untouched.
- **Confirm the engagement was actually in scope before you write the closing summary.** When the user asks whether the
  target you worked is the one they gave you, answer 是/否 in the first line, name the target from their own messages in
  this session, then name what you actually worked on and what it produced. A compacted context carries *other*
  engagements' targets, so a summary's "current target" is not evidence of assignment — only the user's own message is.
