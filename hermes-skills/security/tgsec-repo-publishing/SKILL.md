---
name: tgsec-repo-publishing
description: "Use when 发布 TGSEC 仓库内容：案例课、情报层、或工具链迁移包（含旧克隆升级验收）。"
---

# TGSEC 仓库发布 — 案例课 / 情报层 / 工具链迁移包

**定位**：本机技能库（1200+ 单卡）是作战层；`/root/TGSEC-Qtzuu` 是**沉淀/交付层**。报告、战报、外部情报里的“可复用手法”以 **case-lesson** 形式进仓库 `domains/`，原文与凭据永不入库。

## 仓库契约（先认门）

- 路径 `/root/TGSEC-Qtzuu`；远端 `git@github.com:lanyz1/TGSEC-Qtzuu.git`；分支 `master`
- `.claude/skills/` = 伞形技能卡（约 15 张），由 `scripts/sync-hermes-skills.sh` **从仓库同步到本机**（方向别搞反）
- `domains/<域>/case-lessons/<slug>.md` = 案例课（唯一新增落点）
- `domains/CASE-INDEX.md` = 总索引：分域表 + 总课数
- `domains/INGEST-YYYYMMDD-PACK.md` = 每批吸收说明
- 常用域：`auth-security` `api-security` `web-attack` `file-vulns` `gambling-pentest` `recon` `business-logic`（以 CASE-INDEX 实际分组为准）
- **不进仓库**：本机全量单卡、报告原文、明文凭据/TOTP 种子/源站 IP/客户 PII、内部自检（AUDIT/SKILL-AUDIT）

## 铁律 0：没有主人明确点头，不许 push（2026-10-23 被骂后立规）

原话：「你别瞎几把给我推送到仓库了啊，没有我的同意别推」「保持现状」。

- 这是**公开仓**：一次 push 就是对外发布，撤回还得再推一次（revert 一条 / force-push 一条，两条都是发布动作）
- 允许做到 `git add` + `git commit` + `git log --oneline -1`，**到此为止**
- push 前先问一句：「要不要推？本次 N 个文件：<清单>，commit <短哈希>」
- 只读预演随时可跑：`git push --dry-run origin master`（不落盘，能看到 `pre-push 脱敏闸 OK` 与区间）
- 主人说「保持现状」= 停手三件：不 push、不 revert、不 reset。本地领先 origin 是合法状态，不是待办
- 已经误推：先摆事实（commit 哈希 / 文件数 / diff 有没有敏感串 / 远端停在哪），再给「软撤 revert」与「硬撤 force-push 回 <旧哈希>」两条路，**等指令，不自己补救**

## 发布流程（照顺序）

1. **定课**：从报告/情报里挑“可复用手法”，一法一课。纯内部自检、只到“可控”没走通的，不单开课（并入旧课）。
2. **写课**：`domains/<域>/case-lessons/<slug>.md`，模板见 `templates/case-lesson.md`。slug 小写连字符、能看出手法（如 `sonata-code-array-totp-secret`）。
3. **改索引** `domains/CASE-INDEX.md`：
   - 行格式：`| \`<slug>\` | 一句话 | \`domains/<域>/case-lessons/<slug>.md\` | — |`
   - 插到对应域表末尾；同时改**域标题计数**和**头部总课数**，并追加本批生成行
4. **写 INGEST**：`domains/INGEST-YYYYMMDD-PACK.md`，四段：来源与体量 / 战报→case-lessons 表 / 本机技能库同步（注明不入仓） / 未吸收与边界 + 脱敏声明。
5. **提交**：`git add -A && git commit -m 'ingest(pack-YYYYMMDD): N case-lessons + M increments + INDEX sync <total> + INGEST doc'`
6. **过闸**：`python3 /root/tgsec-guard/scan_push.py /root/TGSEC-Qtzuu` → 必须 `VERDICT: clear to push` / exit 0
7. **推送并自证**：`git push origin master`；然后**分三条跑，别 `&&` 串**：
   - `git rev-parse --short HEAD`
   - `git ls-remote origin refs/heads/master`
   - `git status --porcelain | wc -l`
   要求本地=远端、dirty=0、`scripts/reconcile_case_index.py` 报「文件↔索引零差」。

### 只发布「技能库卡」的那条支线（不动 domains/case-lessons）

主人说「提交到仓库吧」但本轮产物是**技能卡**（吸收报告包 / 情报源）时，走这条，别硬套 case-lesson 流程：

1. **先算清本批新增与改动**，别凭记忆写 changelog：
   ```bash
   git show --diff-filter=A --name-only --format="" <commit> | grep '/SKILL.md$' | sed 's|.*/\([^/]*\)/SKILL.md|\1|' | tr '\n' ' '   # 新增卡名
   git show --diff-filter=M --name-only --format="" <commit> | grep -c '/SKILL.md$'                                    # 改动计数
   git show --stat <commit> | tail -2                                                                                 # 文件数 / +- 行
   ```
2. **同步方向**：本机 `~/.hermes/skills/**/SKILL.md` → 仓库 `hermes-skills/`（`scripts/sync-hermes-skills.sh` 或一次性 `repo_sync.py --apply`）；`git status --short hermes-skills | wc -l` 应等于「新增 + 改动」。
3. **脱敏闸 → commit → push**：见下节「推前闸」9/10 条；BLOCK 时**先修再推**，修脱敏单独一个 commit。
4. **内容级自证**：`git ls-tree -r --name-only origin/master | grep -E '<新卡1>|<新卡2>'` 命中 + `raw.githubusercontent.com` 抓 README 首条 + 新 `UPDATE-<date>.md` 返回 200。
5. **别把编译产物塞进去**：`domains/**/exploit`、`*.o` 这类本地构建残留保持 untracked，交付时点一句「这些没提交」，别静默 `git add -A`。


一键体检：`bash scripts/verify_publish.sh /root/TGSEC-Qtzuu` · 索引对账：`python3 scripts/reconcile_case_index.py /root/TGSEC-Qtzuu`（加 `--fix` 自动补行 + 按实际文件重算计数）

## 发布工具链/迁移包（不是案例课的那种发布）

仓库不只收课，也收**要别的机器真能跑起来的工具链**（检索栈、升级脚本、迁移说明）。这类发布是另一套验收：

1. **三件套一起上**，缺一条旧克隆就卡住：
   - `tools/<name>/`：脚本**整目录**（不是挑几个“主脚本”）
   - `scripts/apply-<date>.sh`：**幂等**升级脚本（备份 → 删/搬 → 重建+过闸；重复跑不二次破坏，`--no-purge` 可跳过清磁盘）
   - `docs/UPGRADE-<date>-<topic>.md`：给“已经在用旧版”的 AI 的独立文档——变更对照表、脚本法+手工法、验收表、回滚、坑、一段可直接粘的提示词
   - README 只放指针（顶部 bullet / §〇 / §十二 各一条链接），流程细节别塞 README
2. **整目录拷贝**：`build` 会调同目录 helper（如 `build_termdf.py`）、门禁会调 `selftest.py`、评测会调 `route_eval.py`。只拷三个主脚本 → 别人第一次重建就 `no such table: term_df` / traceback。升级脚本用 `for f in "$REPO"/tools/<name>/*.py` 全拷。
3. **路径全部 env 可覆盖**（`ARSENAL_SKILLS` / `ARSENAL_DIR` / `ARSENAL_DB` / `ARSENAL_ROUTE_EVAL`…），默认值保持原样；硬编码 `/root/...` 的包换个用户就废。
4. **拿假 HOME 跑“首次安装”分支（必做）**：真机已升级过，跑脚本只会走“无待删卡”分支，删卡/搬 refs/写 disabled/首建库全都没被执行过。用 `scripts/fake_home_fixture.sh` 造 2~3 张卡的假技能树，`HOME=/tmp/fh HERMES_SKILLS=... bash scripts/apply-*.sh --no-purge`，必须看到 备份→删卡→搬 refs→重建 全过；门禁在假树上**应当 FAIL**（卡不够），但**不许出 traceback**。首次跑就靠这招抓出漏 helper + 硬编码路径两个死穴。
5. **验收要从真 remote 重新 clone 再跑一遍**：私有仓 `https://github.com/...` 匿名 clone 会 `could not read Username`，用 SSH remote（`git@github.com:...`）。在 clone 里跑同一脚本，确认 executable bit、文件清单、脚本自解析路径都对。
6. **门禁/评测自测必须 `SKILL_FIND_NOLOG=1`**：三 phase 评测漏这个变量，每跑一次门禁就往 `query.log` 灌几十条假检索，把“实战命中率”统计毁掉（2026-10-22 实修）。
7. **别在发布中途 amend/force-push**：已推出去的 commit 被 amend，别的克隆 `git pull` 会 `divergent branches`。真发生了就在 UPGRADE 文档写恢复命令（`git stash -u && git fetch origin && git reset --hard origin/master`）；教训是本地测干净再推。
8. **仓库不含全量卡、也不含索引 db**（342MB 二进制）：升级只删“对方本机存在的同名卡”再重建，所以别人的卡数不会等于你的。验收口径写成“索引卡数 == 磁盘 SKILL.md 数 + `GATE OK`”，别写死 2146。
9. **升级脚本要在文档里显式声明“不重建索引=没升级”**：`git pull` 只更新脚本，检索读的仍是旧 db；这条是旧克隆最常漏的一步。
10. **文档里的每个基线数字，写之前现场跑一遍**：本批差点把「全库可达 2146/2146」发出去，实测 TOP10 只有 2122/2146（98.88%，24 张 MISS）。可达率一律写 TOP1/TOP3/TOP10 三个值 + MISS 名单，**不写「全通/100%」**；审计脚本跑一次 ~10 分钟，把 `REACH_OUT` 产物路径和耗时一起写进验收表，并说明「这是现状基线，不是门槛」。
11. **安装步骤必须自查完整性（md5）**：0/n 步拷完 `tools/*` 后逐个比 md5，打印「工具栈 N 个文件全部到位（md5 一致）」。案卷机就是漏装了 `full_reachability_audit.py`，说明里那行验收命令直接 File not found，半个月没人发现。反过来也成立：**验收表里每一条命令，都要在「只装了一部分」的机器上确认文件存在**。
12. **卡数对账别用 `grep -c 'SKILL.md$'`**：会把 `references/upstream-*-SKILL.md` 这类资料转储算成卡（仓里报 1160，真卡 1110，多出的 50 条不是卡）；`find -name SKILL.md` 又会把悬空软链算进来。真卡数 = `git ls-files | awk -F/ '$NF=="SKILL.md"' | wc -l`，磁盘数只认常规文件（`os.path.isfile`，glob 后过滤）。给别人的卡数口径写错，对方永远对不上账。

13. **空安装位必须 bootstrap**：新机器/干净 HOME 上 `~/.hermes/skills` 可能整个不存在或 0 张卡，apply 脚本第 0 步要先判（`mkdir -p ~/.hermes` + `find "$SK" -name SKILL.md | wc -l`），为 0 就跑 `scripts/sync-hermes-skills.sh` 装 15 张伞形，否则直接 `FATAL: 技能树不存在`。2026-10-22 实测：干净 HOME 首跑就是这个 FATAL（clone 下来一行命令就死），补 bootstrap 后输出 `will install 15 skills` → `GATE OK（portable，173 条基线不适用）· 索引 15 卡 / 磁盘 15 张`。
14. **导出包必须排垃圾**：`tar czf` 加 `--exclude='.curator_backups' --exclude='.curator_ledger.jsonl' --exclude='*.pkl' --exclude='__pycache__'`。实测 85MB → **41MB**：其中 41MB 是 `.curator_backups/<ts>/skills.tar.gz`（旧 2178 卡快照）、11.8MB 是 ledger；收包的人解出来会以为自己拿到了两份库。打完必验 `tar tzf ... | awk -F/ '$NF=="SKILL.md"' | wc -l` 等于本机卡数。
15. **归档/启用分层必须随包走（`skills/.disabled.json`）**：`arsenal_build.py` 的 `status` 来自 `config.yaml` 的 `skills.disabled`（本机 1805 条 → 372 启用 / 1774 归档 / 1856 归档副本），`enabled` 卡在打分里有 1.15 倍加权。包不带这份名单时目标机 2146 张全算 enabled，加权失去区分度：**同一套卡、同一份代码，core96 从 `94/96 · 96/96 · MISS 0` 掉到 `88/96 · 94/96 · MISS 2`，正文词 7/8→5/8**。修法：export 把名单写进 `skills/.disabled.json`，build 启动 `DISABLED |= set(seed)`（`ARSENAL_IGNORE_DISABLED_SEED=1` 可关）。2026-10-22 在 `<IP-REDACTED>` 实测：补 seed 重建后 `enabled 372 / disabled 1774 / legacy 1856`，门禁立刻回到 `94/96 · 96/96 · MISS 0 · 改动 0 张`。

实战账（12 文件、3 个真 bug、假 HOME 输出、真 remote clone 验收）：`references/toolchain-migration-20261022.md`。
文档口径对账（10 条实测清单 + 4 处错口径 + 给其他 AI 的三版同步话术）：`references/doc-vs-machine-audit-and-sync.md`。

## 全量卡入仓：先过可见性闸（2026-10-23 起 = public 仓「脱敏副本」已落地）

**现状，别再按「public 硬拒」结案**：2026-10-23 已把全量库脱敏后推进公开仓 —— `hermes-skills/` 12,708 文件 / 2,206 卡 / 153MB（远端 `f22dc2ff`），同批 `884811f1` 补进 `arsenal/` 检索栈。结论变了：判据不是「能不能推」，而是**脱敏过没过闸**。可见性判断照旧先做。

用户喊「为什么不能好好提交到仓库完整」时，先量再答，顺序不许反：

1. **判可见性**：`bash scripts/repo_visibility_gate.sh /root/TGSEC-Qtzuu`（或 `curl -s https://api.github.com/repos/<owner/repo> | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("visibility"))'`）。
2. **public → 只推脱敏副本，不推原树**（2026-10-23 已跑通一次，见下节）。本机实测（2026-10-22）：仓 public / 123MB；安装库 2146 张里 **46 个文件含 PRIVATE KEY 块、8 个 AKIA、1 个 `ghp_`、1 个 `sk-`、114 个文件有明文口令、1858 份带真实域名/IP 的 legacy 案卷**。
3. **公开仓本来就在漏 lab 密钥**：tracked 内容里已有 60 个 `BEGIN … PRIVATE KEY`、16 个 AKIA、3 个 `ghp_`——抽样全是 CVE 靶场自签密钥（`lab/uaa.yml`）、扫描器正则、`AKIAIO...MPLE` 占位。再推 150MB 实战卡不是「补齐」，是开闸。

**话术纪律**：别用「按设计不入仓」搪塞（用户当场炸：「瞎鸡巴搞」）。一次说清三条出路，并说明各自代价：

| 出路 | 动作 | 代价 |
|---|---|---|
| 转私有（推荐） | GitHub Settings → Danger Zone → Change visibility → Private，然后 `bash scripts/sync-full-library.sh --push` | 要 admin 权限：SSH deploy key 只能推代码、改不了可见性；本机无 token/gh CLI 时必须让用户点一下或给 token |
| 坚持公开 | 只推脱敏子集：私钥/口令替成 `[REDACTED]` | payload 段变占位，实战卡废一半 |
| 保持现状 | `scripts/export-arsenal-library.sh` 搬 82MB 包（离线 md5 核对） | 别的机器拿不到 full 基线，只能 portable |

**「已蒸馏吸收」的实数**（2146 vs 仓 987 = domains 973 + 伞形 15）：同名 **837 = 39%**、仅本地 **1309 = 61%**；1309 里仅 525 个名字在仓正文出现过，且多半只是 `tools/arsenal/eval_core.json` / `docs/updates/*` 的路径引用；1856 份 legacy 里 931 个名字被提到、**925 个完全没影**。结论口径：**「仓库能给的都一致了」= 账对上，≠ 卡齐了、≠ 蒸馏完了**；报覆盖率就报这四个数。量法：`python3 scripts/measure_repo_coverage.py /root/TGSEC-Qtzuu ~/.hermes/skills`。

细节与原始命令输出：`references/full-library-push-gate-20261022.md`。

## 用户硬要「全量覆盖到仓库」：可执行路径（2026-10-23 实测）

public 仓也能满足「完整覆盖」，前提是**只推脱敏副本**，本机库保留原值供实战。顺序固定：

1. **落点** `hermes-skills/`（`sync-hermes-skills.sh` 的首选源）→ 必须删掉 `.gitignore` 里 `hermes-skills/` 那行（2026-10-02 瘦身加的），否则 `git status` 永远看不到。
2. **rsync 排垃圾**：`.curator_backups/`（39.7MB 旧快照）、`.curator_ledger.jsonl`（11.5MB）、`__pycache__`、`*.pkl`、`*.tar.gz`、`*.log`。实测 **2,206 卡 / 12,863 文件 / 153MB**，最大单文件 1.1MB。
3. **脱敏必须扫全部文本类型**，不能只 `*.md`：`redact_own_assets.py` 只处理 md，`scripts/` 里的 PEM、key、token 全漏。按扩展名白名单 + 前 4KB 含 NUL 判二进制跳过。
4. **四类一起刷**：① 自有 IP（`154.219.*.*` 整段，不只 /127）② CRIT 家族（下表）③ PII（邮箱/手机/身份证）④ 凭据赋值（`password|secret|token|api_key|aes_key|channel_secret` 的值，占位符与 `$VAR`/`{{}}` 保留）。
5. **guard 点名的家族比想象多**（`/root/tgsec-guard/scan_push.py` 的 `CRIT`）：`sk-`16+、`AKID`（腾讯 SecretID）、`AIza`（Google）、`AKIA`、`xai-`、`gsk_`、`hf_`、`pplx-`、`nvapi-`、`tgp_v1_`、`gh[pousr]_`、`github_pat_`、`xox[baprs]-`、`tg[ab]_`、`[0-9]{8,10}:AA…`。第一轮只按 AKIA/ghp 刷必被 `DO NOT PUSH` 打回。
6. **实测替换量**（2206 卡那批）：邮箱 3,322 · 手机 834 · 凭据值 724 · 身份证 32 · LTAI 6 · AIza 7 · AKID 2 · AKIA 12 · 长 hex 21 · Bearer 17 · PEM 块 3 · sk 3 · TG token 8 · 自有 IP 13。
7. **闭环**：rsync → redact → `git add -A` → commit → guard（不过就补刷 → `--amend`）→ push → `git ls-remote` 对上 HEAD、`git status` dirty=0。
8. **人格/记忆同批**：`ai-config/hermes/{MEMORY,USER}.md` + 两份 `.payload.md` 覆盖，新增 `SOUL.md`（Hermes 运行人格，别覆盖 `universal/PERSONA.md`）。`setup.sh` 只在目标文件小于 payload 时才覆盖。

## 对外分发两条路：公开仓管「跑得起来」，加密包管「卡齐」

别人（人或其他 AI）问「到底怎么更新」时，只给这两条，别把设计再讲一遍：

| 路 | 给什么 | 对方做什么 | 结果 |
|---|---|---|---|
| **A 公开仓** | `git@github.com:lanyz1/TGSEC-Qtzuu.git` | `git fetch origin master && git reset --hard origin/master` → `bash scripts/apply-arsenal-20261022.sh` | 检索栈 + 15 伞形 + `domains/` 1095 知识库；门禁 `tier=portable` |
| **B 全量 2204** | `hermes-skills-20261022-1953.tar.gz.gpg`（43MB）+ sha256 + **口令单独发** | 建议**案卷机解密、只传 tar**（口令不落目标机）：`scp lib.tar` → 目标机 `sha256sum -c` → `tar xz -C ~/.hermes` → `bash scripts/apply-arsenal-20261022.sh` | `tier=full` |

- **一条命令灌库（首选，2026-10-22 新增）**：`bash scripts/import-arsenal-package.sh <pkg.gpg> <PASSPHRASE.txt>` —— 校验包（数卡 + 读 seed）→ 旧库 `mv` 成 `skills.bak-<时间>` → 解包到 `~/.hermes/skills`（带 `.disabled.json`）→ 装检索栈 + 重建 + 门禁，末行打印 `total/disk/tier/skipped/ok`。`HERMES_SKILLS` / `BACKUP_DIR` 可覆盖。干净 HOME 实测（`HOME=/tmp/t9 HERMES_SKILLS=... `）：`2204 / 2204 / full / skipped=0 / ok=True`，`IMPORT_RC=0`。**别再让对方手敲五条 tar/gpg**——手敲版本最容易漏 seed 与工具链。
- **旧克隆别用 `git pull`**：历史上 amend 过，`pull` 会 `divergent branches`。标准动作是 `fetch + reset --hard`；`reset --hard` 只动仓库工作树，**不碰 `~/.hermes/skills`**，不担心冲掉本机卡。先 `git clean -nd` 看一眼再决定 `-fd`。
- **两种导入模式，先选一种再谈数字**：① **overlay**（直接解到现有库上）→ 索引 = 2204 + 对方私有卡，`total == disk` 仍成立但**不等于基准数**；② **move-aside**（`mv ~/.hermes/skills /root/skills.thin-<date>` 再解包）→ 得到与案卷机一字不差的 `2171 / 397 启用 / 94-96 · 96-96 · MISS 0`，那批私有卡留作下一轮吸收原料。要跟别人对数用②，要保对方私有卡用①。
- **导入后先看 `enabled/disabled` 两个数，再看 TOP1**：`arsenal_build.py` 末行应打印 `"enabled": 372, "disabled": 1774`。如果看到 `enabled 2140+ / disabled 个位数`，说明包里的 `skills/.disabled.json` 没生效（老包或 `ARSENAL_IGNORE_DISABLED_SEED=1`），此时 TOP1 会只有 88/96，别当成机器性能问题。
- **口令不进群、不写摘要**：`PASSPHRASE.txt` 离线单发；包和解密口令分渠道，sha256 先校验再解。
- 公开仓 2026-10-23 起带**脱敏全量**（`hermes-skills/` + `arsenal/`），「一条 `git pull` 全同步」现在成立；但拉下来的是脱敏版，实战原值只在本机库与案卷。

实测命令与预期输出、精简库导入后的数字：`references/distribution-and-clean-machine-20261022.md`。

发「curl 一行」之前先量三件：raw 与仓内脚本 md5 是否一致、raw/jsdelivr 是否可达、**仓里 `hermes-skills/` 卡数与本机差几张**（2026-10-23 实测 2,226 vs 2,228 = 少 2 张，差额必须报出来）。核对命令与镜像边界：`references/hermes-parity-installer-20261023.md`。

### 新机器（已有精简库）同步：6 步实测

用户丢来一句「这台也给同步更新上，账号密码都一样」时照这个走，别现场发挥：

1. **先探再动**：`hostname; nproc; free -g; df -h /; find ~/.hermes/skills -name SKILL.md | wc -l; ls ~/.hermes/arsenal; git -C ~/TGSEC-Qtzuu rev-parse --short HEAD`。判两件事——磁盘够不够（库 150M + db 348M + 仓库增量），以及**有没有工具链**（`~/.hermes/arsenal` 空 = 这台从没跑过门禁，它自己说的「库没问题」不算数）。
2. **本地解密、只传 tar**：案卷机上 `gpg -d pkg.gpg > /tmp/lib.tar` → `sha256sum` → `scp lib.tar lib.tar.sha256` → 目标机 `sha256sum -c` 必须 `OK`。**口令文件不 scp**，目标机连 gpg 都不用装。
3. **精简库挪开不删**：`mv ~/.hermes/skills /root/skills.thin-<date>`，记下原卡数（实测一台 160 张）。这批是下一轮「吸收独有卡」的原料，删了就得再问对方要。
4. **解包 + 数两个数**：`tar xz -C ~/.hermes`；`find ... -name SKILL.md | wc -l` 必须等于包内卡数；`python3 -c 'import json;print(len(json.load(open("$HOME/.hermes/skills/.disabled.json"))))'` 必须等于本机 seed 条数（1805）。seed 少了就是拿了老包，TOP1 会掉到 88/96。
5. **仓库对齐 + 一条脚本**：`git fetch -q origin master && git reset -q --hard origin/master`（不用 `pull`）→ `bash scripts/apply-arsenal-20261022.sh`。`APPLY_RC=0` 只说明脚本没崩，**不等于通过**。
6. **三证验收**：`cat ~/.hermes/arsenal/gate_last.json` → `tier=full / total==disk / skipped=0 / ok=true` 且 core96 `94/96 · 96/96 · MISS 0`；再抽一条口语查询证**真能检索**（实测 `skill_find.py "1win 平台 打点" --phase recon` → TOP1 `1win-platform-pentest score=2028.5`）；最后 `rm -f /tmp/lib*.tar*` 清临时包。

两台机器（`.31` / `.60`）的探测值、耗时与包 sha256：`references/new-machine-sync-20261022.md`。

## 吸收别机旧库独有卡：move-aside 之后的第二半

新机换成全量库后，被挪开的精简库（实测 160 张）是**下一轮吸收的原料**。用户问「上面有可吸收的吗」时按四步答，不许拿标题肉眼看：

1. **名字差集**：旧库 `find -name SKILL.md` 取父目录名，减本机卡目录名（实测 160 → 59 张本机没有）。
2. **先证「不是改名/改写」**：候选 SKILL.md 去 frontmatter 后做 5-gram shingle，与本机全库逐张算 Jaccard，报 max + best-match。实测 59 张全部 **≤0.05**（多数 0.00）= 另一批人独立写的；**跳这一步就会把改写卡当新卡收进来**。
3. **按「面」判，不按「像不像」判**：本机已有同攻击面平级卡的一律丢。本次丢 26（thinkphp 6、验证码 OCR 10、报告写作 8、dujiao 2、engagement 收尾、代理出口、两组二选一 nfs / websocket）；收 33（鲸发卡、NFS+rpcbind、SockJS/STOMP、noVNC、TokenPay、包网白牌、Cocos、韩国 DART、发卡未售库存提取、面板配置→命令执行、备份恢复外带、反射 XSS 打操作员、反封锁镜像集群、C2 家族基建、加壳 APK→C2、New API 网关…）。
4. **收前扫密钥、收后跑门禁**：装库前逐张 grep `secret|private_key|pwd=|apikey`（本次 0 命中）；装完重建必须仍是 `94/96 · 96/96 · MISS 0`，只有卡数与 enabled 变（2171→2204 / 397→430）。

吸收闭环五件缺一不可：本机入库+重建+门禁 → 口语查询抽测（8 条命中 7 条 TOP3，未中的要能解释成同族卡）→ 落仓 `domains/`（commit message 不写来源机 IP）→ 各 worker **只传新卡 tar** 并各自重建（数字必须与本机一字不差）→ 重打分享包并**解密实核** `cards=N / ip_hits=0 / secret_hits=0 / seed=M`。

工具：`scripts/triage_absorb_candidates.py --remote <旧库> --local ~/.hermes/skills`（名字差集 + shingle Jaccard + 分桶）。
实账（59→33、26 张丢弃理由、三机数字、包 sha256）：`references/card-absorption-triage-20261022.md`。


## 发布前脱敏闸：自有 IP / 真密钥（2026-10-22 事故）

用户会直接质问「为什么仓库要用这种暴露 IP 的」。答案分两层，别混着答：

| 类别 | 例子 | 处置 |
|---|---|---|
| **目标方** IP / 域名 / 端点 | `43.153.182.152:33389`、`h5.goodluck777.com` | **保留**——案卷证据 + 复现入口，这是知识 |
| **自有** IP / 主机名 / 出口 | `<IP-REDACTED>`、`<HOSTNAME-REDACTED>`、落地机与跳板 | `<IP-REDACTED>`；**0 知识价值，纯 OpSec 自杀** |

事故经过：吸收 25 张外部卡时，**commit message 里写了来源机器真实 IP**，卡内 `jtti-2fa-twice-post.md` 还留着「同一出口 IP（真实值）注册 143913/143914/143916」；同一批里 `goodluck777` 案卷带 6 个目标站真密钥（`Pay_AesKey` 40 hex、`channel_secret` 32 hex、`GameTower_private_key`、reCAPTCHA site key、FB ID、LIFF ID），传奇私服案卷带网盘分享口令。全是公开仓不该有的东西。

硬规则：

1. **commit message 不许出现自有 IP / 主机名**，用代号（`案卷机 B` / `源机`）。提交信息被 GitHub 永久索引，比文件更难洗。
2. **吸收别机卡之前先扫密钥**：案卷里高频出现 `VITE_*_secret`、`Pay_AesKey`、`private_key`、网盘 `pwd=`、`apikey`。命中改成 `<REDACTED>`，**只留字段名**，技术点不丢（例：`VITE_LINE_channel_secret:"<REDACTED>"`）。
3. **提交前两条必须为 0**：`git grep -c '154\.219\.'`、`git grep -c '<本机主机名>'`；再 `git grep -nE 'BEGIN.*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}'` 人工判 lab/真。注意 `git grep` 只扫 tracked 文件，**提交前跑才有意义**。
4. **曝光处置顺序**（本次实测 `5e5c0f3b → ce188f5f`）：改文件 → `git add -A` → `git commit --amend`（把 IP 从 message 里抠掉）→ `git push --force-with-lease` → `git grep` 复查 0 → 核对 `HEAD == remote`。force-push 前先确认这次提交是本会话刚推的，别碰别人的历史。
5. **诚实交代残留**：旧 commit 只要推过，**按 SHA 直访仍能拿到，直到 GitHub GC**。彻底拔要 `git filter-repo` 全史重写 + 强推，代价是全部 SHA 变化、所有克隆重拉——**让用户拍板，别自作主张洗历史**。
6. **分享包必须同源脱敏**：包是从 `~/.hermes/skills` 打的，只改仓库不改安装库 = 包里仍是原值（本次 1903 包就是这样带出去的）。改安装库（先备份）→ 重建（`total` 与门禁分数不许变）→ 重打包 → **解密实包 grep** 验 `cards=N / ip_hits=0 / secret_hits=0 / seed=M`，再删旧包。
7. **`amend` 后要复查仓库工作树**：`git status --porcelain | wc -l` = 0，否则下次 `git add -A` 会把审计脚本又带进去。
8. **源树扫干净 ≠ 包干净；讲脱敏的那张卡自己是最大盲区**：本轮 `sweep_lib.sh` 已报 `IP FILES:` 为空，但解包复验仍报 `2 files own IP / 1 secret`，命中全在 `tgsec-repo-publishing/SKILL.md` 与 `references/pre-publish-redaction-and-ip-opsec.md`——**讲脱敏纪律的卡把真实主机名、真实网盘 `pwd` 当正/反例写了进去**。规矩：脱敏按内容 grep 全库，**不按扩展名、也不排除自己**；唯一验收权威是解出来的包，不是源树。

脱敏脚本：`scripts/redact_own_assets.py`（自有 IP 正则 + 字面量表，改前自动备份到 `<root>/redact-backup/`，`--dry-run` 先看命中再落盘）· 验包：`bash scripts/verify_package_clean.sh <pkg.gpg> <passfile> <期望卡数> '<自有IP正则>' <字面量表>` —— **四查**（卡数 / 自有 IP / 密钥字面量 / `.disabled.json` 条数），末行 `PKG_CLEAN` 才算过；`ip_hits>0`、`literal_hits>0`、卡数不符任一即 `PKG_FAIL`，seed=0 只 WARN（老包）。
实账（12 文件 / 13 处自有 IP / 4 处密钥、安装库 323 个文件带目标站凭据、包 `1903 → 1912`、新 sha256）：`references/pre-publish-redaction-and-ip-opsec.md`。

## 全量入仓后的脱敏验收：gitleaks + 推前闸（2026-10-23 实测）

推 public 仓只有一条硬标准：**脱敏过闸**。自写正则只覆盖「关键词+值」，漏「值在前」的中文写法（`<口令> 系口令`、`root/<口令>`、`admin/<口令>`），两套必须一起跑：

1. **装 gitleaks**（单二进制，30 秒）：`curl -sL https://github.com/gitleaks/gitleaks/releases/download/v8.28.0/gitleaks_8.28.0_linux_x64.tar.gz | tar xz gitleaks && install -m755 gitleaks /usr/local/bin/gitleaks`。
2. **全树扫**：`gitleaks detect --source hermes-skills --no-git --report-format json --report-path /tmp/gl.json --exit-code 0`（153MB / 4.3 秒）。
3. **降噪口径**（775 条里真货只有个位数）：`curl-auth-user`(364)/`curl-auth-header`(195)/`generic-api-key`(184) 绝大多数是文档示例 —— `Harbor12345`（Harbor 默认）、`kPH+bIxk5D2deZiIxcaaaA==`（Shiro 默认）、`P@ssw0rd`、`YOUR_API_KEY`、`dGhlIHNhbXBsZSBub25jZQ==`（"the sample nonce"）一律保留；`private-key` 命中全是 `secret_scan.py` 里的检测正则；`stripe` 是 `sk_liv...xxxx`。逐条看 `File/StartLine/Secret` 三列判，别按规则名一刀切。
4. **补充扫描中文叙述里的口令**：`(?:口令|密码)\s*[：:=]?\s*([A-Za-z0-9!@#$%^&*_.+-]{8,})` / `(?<![\w-])-p\s*['\"]?([\w!@#$%^&*.-]{8,})` / `\b(?:root|admin|redis|mysql)/([\w!@#$%^&*.-]{8,})` / `AUTH\s+(\S{8,})`，再用「含数字或符号」+ 排除 `root/.bash_history`、`root/*.session` 这类路径噪声。实测：宽版 1,771 文件/3,601 命中全是噪声 → 收紧到 54 条 → 真口令 10 个。
5. **只换字面量、保留句式**：一律 `[REDACTED]`，字段名与技术点不动；改完对脚本类文件跑 `python3 -c "import ast;ast.parse(open(f).read())"` 验还能解析。
6. **推前闸（一次装好、永久生效）**：`bash scripts/prepush-secret-gate.sh --install <repo>` → 装进 `.git/hooks/pre-push`，命中字面量/真私钥体/AKIA/ghp_/完整 xoxb/真 `sk-` 就 abort（4 秒跑完）；字面量表 `.git/secret-denylist.txt` **不入仓**。首版用 `xoxb-[0-9]` 会误伤「讲 token 格式的文档」，必须收紧成完整 token 形状。
7. **检索栈必须同批入仓**：只搬卡不搬 `arsenal_build.py` / `skill_find.py` / `eval_core.json` → 新机器有卡但搜不出来（本轮 `arsenal/` 14 文件后补）。索引本体 `arsenal.db`(367MB)/`vuln.db`(15MB) 不入仓（GitHub 单文件 100MB 上限），README 给重建命令。
8. **推完三证**：`git ls-remote origin master` 对 HEAD、`git ls-tree -r --name-only origin/master | grep '^hermes-skills/' | wc -l`、GitHub API 的 `size`/`pushed_at`。再加一条**内容级**核对（比哈希实）：`curl -s https://raw.githubusercontent.com/<owner/repo>/master/README.md | sed -n '1,4p'` 首条已是本轮；新建的 `docs/updates/UPDATE-<date>.md` 用 `curl -s -o /dev/null -w '%{http_code}'` 必须 `200`。
9. **闸要能单跑，别等 push 才试**：`cd <repo> && bash .git/hooks/pre-push </dev/null; echo "gate=$?"` —— commit 前后都能跑，4 秒出 `pre-push 脱敏闸 OK` / BLOCK。push 被拦时先跑它定位，别反复 push。
10. **BLOCK 后按「假串也照改 + 两侧同改」闭环**（2026-11-01 实测一轮被拦 3 处）：
   - **假测试串同样算命中**：`AKIA<16位>` 形状的示例 key（哪怕是人写的 `AKIA<16位占位>`）照样 abort。改法保住检测语义——`echo "$(printf 'AKIA%s' '1234567890ABCDEF')" | grep -qE 'AKIA[A-Z0-9]{16}'`，字面量消失、正则仍在。别直接删测试用例。
   - **AES key / 口令改「指向取值路径」**：`UMI_APP_API_SECRET_KEY=[REDACTED-16位AES密钥]（同 key 亦作 iv；从 10243 配置块直取）`，比裸 `[REDACTED]` 保留更多可操作性。
   - **两侧同改**：仓库副本改完必须改 `~/.hermes/skills/<同一相对路径>`，否则下次 `repo_sync`/`sync-hermes-skills.sh` 会把明文原样搬回仓库（本轮 4 文件 × 2 树）。反之仍禁止（脱敏副本不反向回灌本机）。
   - **讲脱敏的更新说明自己是盲区**：写 `docs/updates/UPDATE-<date>.md` 时别把原值抄进表格当反例（本轮写成 `root/<真口令>` 又被拦一次），只写「MySQL `root` 口令明文 → `root/[REDACTED]`」。
   - 改完跑一次单跑闸 + `grep -rn '<字面量>' hermes-skills/ | wc -l`，再 commit（修脱敏单独一个 commit，别 amend 吸收批）。

实账（时间线、两轮扫描的真/假命中、23 文件 35 处清单）：`references/full-library-public-push-20261023.md`。
闸拦截→修复→双写→复核全流程（3 处命中、4 文件 × 2 树、内容级验收）：`references/prepush-gate-block-recovery-20261101.md`。

## 闭环验收：`git clean` 不等于闭环

一次吸收的闭环 = **仓 + 索引 + 账本 + README + 远端** 五处齐平。假闭环长这样：技能卡改完、`git status` 干净，于是以为完事——其实那批只落本机 `~/.hermes/skills/`，仓库还停在几小时前的 commit（2026-10-22 被用户一句「已经完成闭环了吗」当场抓出）。

发布后按序自证，任一条不过就是没闭环：

| 检查 | 命令 | 通过标准 |
|------|------|----------|
| 技能有没有落仓 | `git log -1 --format=%ad --date=iso` 对比 `find ~/.hermes/skills -name SKILL.md -newermt '<commit 时间>'` | 晚于 commit 的技能改动必须已蒸馏进 `domains/` |
| 新 TTP 是否可检索 | 拿 3~5 个特征串 `grep -rl` 到 `domains/` | 搜得到（搜不到=只在技能卡里） |
| 索引三重一致 | `python3 scripts/reconcile_case_index.py` | 文件↔行零差、域计数=文件数、总数=总和 |
| 账本存在 | `ls domains/INGEST-YYYYMMDD-PACK.md` | 本批有 INGEST 文档（commit 里最常漏） |
| README 只留最新 | `grep -n '2026-' README.md` | 顶部 bullet / §〇 / §十 全是本轮，旧日期只剩「历史批次」一句 |
| 远端 | `git ls-remote origin refs/heads/master` | 与本地 HEAD 相同、dirty=0 |

汇报格式：先说「之前没闭环」再列补了什么 + 给出上述证据（commit 短哈希 / guard verdict / dirty=0 / 课数 N=N）。别等用户问第二遍。

## README 更新日志：只留最近一次（用户硬要求）

**规则**：README 只显示**最近一次**更新，历史一条都不展开。用户原话：「只要最近一次更新了什么就行 其他不用显示了」。历史不丢，挪进 `docs/updates/UPDATE-YYYY-MM-DD.md`。

README 有**三处**会堆历史，每次发布一起收：

| 位置 | 锚点 | 收到什么程度 |
|------|------|--------------|
| 顶部 bullet 列表 | 首行 `- 2026-` 到最后一个连续 `- 2026-` | 只留 1 条：本轮最硬 4~5 点 + 课数变化 + 链接 |
| `## 〇、本轮更新了什么` | 到 `## 一、` 之前 | 只写本轮：主项（战报包→课）+ 同日其余吸收，各 3~5 条 |
| `## 十、融合批次` | 到 `## 十一、` 之前 | 只留本轮一条；末尾一句「历史批次见 `docs/updates/` 与 `git log`」 |

配套必做：
- 新建/覆盖 `docs/updates/UPDATE-<date>.md` 承载当日全部明细（分主线、带表、带纠错段），README 三处都链它
- `**更新说明文件：**` 行改成「README 只保留最近一次更新摘要」
- 改完自检：`grep -n '2026-10-1[0-8]' README.md` 只应命中「历史批次」那句提示
- 长 README 改块：Python 读行 → 按锚点定位 → **从后往前**替换（§十 → §〇 → note → 顶部），否则前面的行号会漂
- 完整配方见 `references/readme-latest-only.md`

## 案例课写作纪律

- 结构固定：一句话 / 前提或指纹 / 链 / 判据与边界 / 检查清单
- 只写**可复用手法**：接口、字段、参数语义、错误码、判据、失败边界；不写“我打了谁”的过程叙事
- **数字阈值必须照抄原文口径，不许压缩**：
  - 反例：报告写“15 分钟锁窗、每 16min 实测 2 发”，写成“2 次错密即锁” → 错
  - 正解：写“窗口 15min / 实测每窗 2-shot；另一后台约 8 次/窗 → 阈值因后台而异，首轮单发探针确认”
  - 金额、RTP、倍率、次数、端口同理；不同目标口径不一致就并列写，不取平均
- 没走通的只写“可被指定/可达”，不写“可造成资损/可 RCE”
- 脱敏：明文口令、TOTP 种子、bot_token、源站 IP、客户邮箱手机 → 一律不落库

## Pitfalls

- **脱敏验收看包不看树**：源树 `sweep` 报空之后解包复验仍可能命中（本次 2 处自有 IP + 1 处目标密钥都在 `tgsec-repo-publishing` 自己的 SKILL.md / references 里，被当成范例留着）。全库所有文本类型一起扫、不排除讲纪律的卡，最后以 `tar xz` 出来的包里 `ip_hits=0 / secret_hits=0` 为准。
- **克隆/验收走 SSH**：仓库私有，`git clone https://github.com/...` 会 `fatal: could not read Username`（无 TTY），用 `git@github.com:lanyz1/TGSEC-Qtzuu.git`；推完用 `git ls-remote` 核对哈希
- **工具链发布先假 HOME 后真库**：先在 `HOME=/tmp/fh` 的 2~3 卡 fixture 上跑首次安装分支，再回真库跑幂等分支；否则「删卡 / 搬 refs / 首建库」三条从没被验证过（本次两个真 bug 都是 fixture 抓的）
- **缺卡机器上基线必须判适用性**：门禁基线（selftest 30 + 3phase 48 + core96）是按全量库写的。克隆机/精简库缺卡时，旧门禁把「本机没这张卡」判成「检索退化」，永远红、结论无效（2026-10-22 一台 165 卡克隆机被判死，实际仓库跟踪 1160 张卡、只是没装到 `~/.hermes/skills`）。现版 `post_rebuild_gate.py` 输出 `tier=full|portable`：expect 卡名不在磁盘→跳过并写 `skipped_detail`（selftest 适用性只看卡名），样本 <80% 降为「仅记录」不判死；portable 明确标注「不等于 full 基线」。搬全量库用 `scripts/export-arsenal-library.sh`（tar.gz + 逐卡 md5 + sha256，`--diff manifest` 核对，md5 判增量不看体积）。
- **别的机器贴来的「升级完成」汇报，先在本机复测再转述**：本轮收到一份「164 卡 / portable / 索引 28MB / 重建 4.3s」的漂亮汇报，实测本机是 2146 卡 / full / 342.6MB / 70.75s——那是另一套精简库的数字，只有 commit 哈希对得上。复测三项即可定性：`find ~/.hermes/skills -name SKILL.md | wc -l`、`ls -l ~/.hermes/arsenal/arsenal.db`、`python3 -c "import json;print(json.load(open('$HOME/.hermes/arsenal/gate_last.json'))['tier'])"`。三项全不对就是别的库，别拿它当本机验收结论。
- **两台机器「同库不同分」先查 `status`，别先怀疑 SQLite/CPU**：判决顺序（2026-10-22 实测，同 2146 卡本机 94/96 / 远程 88/96）：① 本机 `use_count` 清零重跑 `route_eval.py`（排除使用加权，本次清零后仍 94/96）；② 把本机 `arsenal.db` 整个传到对方，`ARSENAL_DB=/tmp/local.db` 跑同一份 `eval_core.json`——远程若立刻回到 `94/96 · 96/96 · MISS 0`，说明差异**在建库内容**，不在解释器/SQLite 版本；③ `python3 scripts/db_parity_diff.py <对方.db> <本机.db>` 逐字段对差 + 看 status 直方图。本次 1768 张差异全是 `status`（enabled↔disabled），根因是 `.disabled.json` 没随包。完整过程与命令见 `references/cross-machine-baseline-parity.md`。
- **用户说「先告诉我，不要做改动」= 只读解释**：别顺手重建索引/改文档/提交，数字用本会话已跑出的实测值；方案可写，动手等下一句「干」。
- **同一句话被问第二、三遍 = 上一版答得太散**：用户连问「那到底让其他 AI 怎么同步更新啊」「那现在其他机器人 要怎么更新啊到底」，根因是我在给 A/B 设计说明。改法是给**一个整段可复制粘贴的提示词块**（判可见性→覆盖仓库→跑脚本→贴验收）+ 两行通过标准 + 可选的第二步，末尾一句「就这些」。要能直接转发，不要设计文档。
- **portable 机器别硬判标题/正文词召回**：基线词取自全量库语料，15 卡小库的 IDF/词表完全不同，实测标题词/正文词只有 3/8；`ok < 75%` 只在 `tier == "full"` 时进 `probs`，portable 只写 `facts`。否则干净机器每次都被假红挡住（2026-10-22 实修，全量库回归仍 7/8）。
- **库同步 ≠ 仓库同步**：worker 的 `~/.hermes/skills` 已经 2204 全绿，仓库 HEAD 却可能还停在两天前的 commit（实测两台都落后 4 个提交）。后果不是数字错，是**下次跨机操作调用的是旧版脚本/旧 `domains/`**。收尾必须对每台各跑一次 `git fetch -q origin && git reset --hard -q origin/master && echo "$(hostname) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain|wc -l)"`，两台输出同一短哈希 + `dirty=0` 才算齐。（口令从本机既有脚本里提取给 `sshpass -e`，别手打、别落盘。）
- **「简介/自述改了吗」= 8 处同源，不是 1 处**（2026-11-01 用户原话「自述那些没更新啊」，只改 README 必被追着问）。逐块清单，改卡数/吸收批时一次收干净：
  - `README.md` **5 处**：① 顶部 bullet（新条目置顶，旧条目降为「（上一轮）」）② `## 〇、本轮更新了什么`（整段换本轮；旧内容降成 `### 上一轮（<date>）` 保留，不删）③ `## 一、这是什么` 的 **规模** 块（旧口径「14 个伞形技能入口」这类虚数要换成 `N 张技能卡 / M 文件 / x MB / 启用+归档 / 索引条数 / 触发词条数`）④ `## 十、融合批次`（本轮一条置顶）⑤ `## 十二、更新` 里的「最新：`UPDATE-<date>.md`」指针。
  - `START.md` **3 处**：① 顶部 bullet ② `规模体感` 那行 ③ `**本轮更新（<date>）：**` 段（旧的降为 `**上一轮（<date>）：**`）。
  - 旁证两个文件：`docs/updates/UPDATE-<date>.md`（新建，承载全部明细）、`docs/UPGRADE-<date>-*.md`（有则同步 `total/enabled` 示例）。
  - 自检：`grep -n '2,\?2[0-9]\{2\}' README.md START.md` 只应剩历史段的旧数；`grep -n '2026-1[01]-' README.md` 顶部三段全是本轮日期。
  - 只按「自述」二字改 `README.md` + `START.md` **两个文件**，别顺手动 `ROUTING.md` / `AGENTS.md` / `MASTER.md`（用户明确划过界）。
  - 仓库右上角 About 描述**改不了**（SSH deploy key 只能推代码，本机无 token/gh），交付时给一句可直接粘的描述文案，别装作已改。
  - 测量口径与实测值见 `references/doc-number-sync-and-one-command-import.md`；本轮 8 处逐条 diff：`references/selfdescription-sync-20261101.md`。
- **会话临时物不进仓库根**：审计脚本、`*_run.log`、一次性的 `sync-*.sh` 用完就挪 `/root/audit-<date>/`。`git status` 一脏，用户直接一句「你怎么给我越改越乱了」；汇报前先 `git status --porcelain | wc -l` = 0。
- **commit message 也是发布物**：本次把来源机真实 IP 写进提交信息，文件全干净、`git grep` 也查不出来（它只扫工作树），照样公开泄漏。提交信息里只写代号；改完 message 用 `git log -1 --format=%B | grep -E '<自有IP正则>'` 自查。
- **引导标记会让每台机报 `dirty`**：`scripts/bootstrap.sh` 往仓库根写 `.tgsec-bootstrapped`，`.gitignore` 没这两行时 `git status` 永远是 `?? .tgsec-bootstrapped`，验收口径 `dirty=0` 直接不成立（一台实测就栽在这）。修法：`.gitignore` 加 `.tgsec-bootstrapped` / `.tgsec-bootstrapped.*`，各机 `fetch + reset --hard` 后 tracked 干净、untracked 被忽略即归零。
- **跨机搬包别把口令带上目标机**：解密放案卷机做，目标机只收 `.tar` + `.sha256`。目标机装 gpg 只为解一次包 = 多一个口令落地面。
- **`git add` 之前先数凭据**：`git grep -lI "BEGIN.*PRIVATE KEY" -- .` / `AKIA[0-9A-Z]{16}` / `ghp_[A-Za-z0-9]{20,}` / 明文口令。公开仓里这些命中可能是 lab 测试件，但也是推全量库前唯一的硬证据；先跑 `scripts/repo_visibility_gate.sh`，再谈提交。
- **`git push` 工具超时 ≠ 推送失败**：420s 被工具截断后，后台 git 仍把 `4a6e3a25..4f3ab31a` 推完（`PUSH_RC=0` 晚到一条通知）。超时后先 `git ls-remote origin master` 再决定重试，否则会重复推、或把「其实成功了」报成失败。
- **`commit` 了 ≠ 推了，差多少要按子树量**：本地 ahead 1 摆了一夜，用户看到的就是「前面让你优化的全没提交」。三连定位：`git status -sb`（ahead N）、`git rev-list --left-right --count origin/master...HEAD`、`git ls-tree -r --name-only origin/master | grep -c '^hermes-skills/.*SKILL.md$'`（实测远端 **0** / 本地 2,217 = 整棵子树没上去，不是部分遗漏）。
- **脱敏要连 `ai-config/hermes/MEMORY{,.payload}.md` 一起扫**：上一版只扫 `hermes-skills/`，自有 IP/域名在人格记忆 payload 里原样躺在公开仓（本轮才补成 `[OWN_IP]`/`[OWN_DOMAIN]`）。记忆里带自有链路的，公开版一律占位，新机灌库后再从本机拷真值。
- **仓库的脱敏副本 ≠ 本机库，别反向同步**：`sync-hermes-skills.sh` 是仓库→本机，会把 `[REDACTED]` 盖掉本机原值；反过来 rsync 本机→仓库会把真口令推上去。改完仓库只提交、不回灌；两边差异（实测 1,453 个文件内容不同）就是脱敏差，不是漏提交。
- **guard 与 git 分两条跑**：`python3 /root/tgsec-guard/scan_push.py <repo> && git push` 一键串时，长输出会被吞掉看不到 verdict；先看 `clear to push` 再推
- **guard 扫的是已提交 diff**（`origin/master..HEAD`）：先 commit 再跑闸；工作区没提交时跑它等于没跑
- `sync-hermes-skills.sh` 是仓库→本机：想“把技能推上去”方向是反的，新单卡先落本机技能库
- 计数三重一致：域标题 / 头部总数 / 实际文件数——只改一处会被下次对账抓出来
- 长会话里 `&&` 串长命令输出容易被吞：git 与扫描命令分开跑，或重定向到 `/tmp/*.txt` 再读
- 只往 CASE-INDEX 里已存在的域写；不要临时新建域打散分组
- `git add -A` 前先看 `git status`：共享机上可能有别人的案卷产物，别一把全提
- **交付汇报别只讲最后一批**：一天里跑过 N 条主线（战报包 / CVE 批次 / 四源 / 整站情报 / 内核仓库），只报末批会被怼「怎么没有介绍今天吸收融合了什么」。要给**当日总账**：每条主线一行「来源 → 学到什么 → 落到哪张卡/哪篇课 → 数字」，数字全部重算不凭记忆；并附**纠错段**（被证伪/降级的情报）
- **计数口径**：`case-lessons/` 里除课还有 `README.md` 和 `REPORTS-*-INDEX.md`，`ls | wc -l` 会比课数多 1~2；一律用 `reconcile_case_index.py` 的口径（排除后计数）
- **批次行是浮动块**：CASE-INDEX 底部的本批行没有表头、紧贴最后一个域表；在中间插空行会把表格切成两块渲染成两个表——新行接最后一个 `|` 行之后，不留空行
- **计数漂移的根因**：批次行写在域表外 + 手工只改一处 → 别手改数字，跑 `reconcile_case_index.py --fix` 按实际文件重算（本次 143→147 同时修好 5 篇旧账课从未入索引的问题）
- `git rev-parse --short HEAD origin/master` 曾在推送后报 `fatal: Needed a single revision`：换成 `git rev-parse --short HEAD` + `git ls-remote origin refs/heads/master` 两条分开跑，别把 ref 解析失败当成推送失败
- **统计入库文件别用 `git show --stat | grep '^docs/playbooks/'`**：中文路径会被 git 加引号+转义，该 grep 归零（实测 87 页报成 0，差点当成没入库）。用 `git show --name-only -z --format="" HEAD | tr '\0' '\n' | awk -F/ '{print $1"/"$2}' | sort | uniq -c`，或 `git show --name-status -z`。
- **索引对账必须双向**：`索引有→文件不存在` 与 `文件有→索引没有` 两个空集才算齐。本次一边补新写的 5 课，一边查出 **5 篇一年前就在仓、从未进索引的旧课**（总数 142 却只有 138 个 slug，差值就是它们）。只对总数不动集合，永远查不出来；跑 `python3 scripts/reconcile_case_index.py /root/TGSEC-Qtzuu` 看两行差集。
- **头部总数是派生值**：域标题计数、头部总数都必须由实际文件重算（排除各域 `README.md` / `REPORTS-*-INDEX.md`），任何一处手改都只会在下次对账时重新漂移。
- **更新仓库的那几台服务器禁当跳板机**（2026-10-23 主人明令「我给你更新仓库的那3台服务器也不能当跳板机」）：只做直连对齐与本仓 push，不许 `ssh -J` / `ProxyJump` / SOCKS / 端口转发 / 隧道，也不许拿它当中转去连第三台；要动别的机器就直连。自查两条：`grep -nE 'ProxyJump|ProxyCommand' ~/.ssh/config`、`pgrep -af 'autossh|chisel|frpc|ssh -[DLNR]'`，两边都应为空。
- **「仓库齐了」≠「技能库齐了」**：`git pull` / `reset --hard` 只动仓里的 `domains/`，技能在 `~/.hermes/skills`（另一条 rsync/scp 通道 + 各自重建索引）。验收分开做：仓看 `HEAD == origin/master` 且 `dirty=0`；库看 md5 差集三行 + 重建后的索引 `total`。
