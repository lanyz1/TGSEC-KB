# 升级指南：技能库 2178 → 2146 → 2204 + 检索/门禁换代（2026-10-22）

> 给**已经在用旧版仓库**的 AI / 机器看。人类只需要跑两条命令。
> 转发用短版：[`ANNOUNCE-20261022-ARSENAL.md`](ANNOUNCE-20261022-ARSENAL.md)

## 0. 一句话

旧版：2178 卡（启用 379 / 归档 1799）、索引 346MB、**没有全文召回、没有重建门禁**。
新版：**2204 卡（启用 430 / 归档 1774）**、索引 342MB、三通道检索、重建后 8 项门禁。

**升级 = 拉代码 + 跑一个脚本 + 重建索引。不重建索引会继续检到已删的卡。**
**要 full 基线（案卷机同款满血库） = 拉代码 + 一条 `import-arsenal-package.sh` + 口令。**

## 1. 谁需要升级

- 2026-10-22 之前拉过本仓，并且本机跑过 `~/.hermes/arsenal/` 索引的；
- 本机技能树里存在 `redteam-*-detail-pack` 这类模板卡的；
- 本机 `post_rebuild_gate.py` 不存在 / 少于 8 项检查的。

## 2. 变更摘要

| 项 | 旧 | 新 |
|---|---|---|
| 卡数 | 2178（启用 379 / 归档 1799） | **2204（430 / 1774）** |
| 删卡 | — | 31 张 `redteam-*-detail-pack`（同一段边界样板换域名）+ `laravel-app-pentest`（被 `laravel-pentest` 全覆盖） |
| 停用 | — | `apple-notes` `apple-reminders` `findmy` `imessage` `sdlc-review` `teams-meeting-pipeline`（macOS/办公卡，Linux 跑不了） |
| 胖 refs | `72stack-sec/references/h1-reports` 46MB/3035 份在技能树内 | 搬到 `/root/archive/72stack-h1-reports`，卡留着，卡内路径已改 |
| 索引 | 346MB，只有 description/tags 打分 | 342MB，`body_fts`（FTS5 trigram）全文召回 + `headings` 进粗排 |
| 权重 | 中文单字当强关键词（`调` 撞「回调/调试」） | 单字权重 0.2（ASCII/中文一致） |
| 门禁 | 无 | 8 项，任一红 exit 1 |
| 磁盘 | skills 316M + arsenal 579M | skills 201M + arsenal 366M（回收 ≈325M） |

检索命中率基线（本机实测，你的机器卡数不同会略有差异）：
`core96 TOP1 94/96 · TOP3 96/96 · MISS 0` / `selftest 30/30` / 全库 TOP10 可达 **2122/2146（98.88%）**，24 张断词卡待补。

## 3. 方式 A：脚本（推荐）

```bash
cd TGSEC-Qtzuu
git pull origin master
bash scripts/apply-arsenal-20261022.sh
```

> 若 `git pull` 报 `divergent branches`（本批中途 amend 过一次历史）：`git stash -u && git fetch origin && git reset --hard origin/master`，再跑脚本。

脚本做 6 步，**幂等**，重复跑不会重复删：

0. 安装位为空（新机器/克隆机）时先自动 `sync-hermes-skills.sh` 装 15 张伞形卡，否则后面无卡可建索引
1. 把仓库版 `tools/arsenal/*` 装到 `~/.hermes/arsenal/`（覆盖旧版，装完逐个 md5 自检）
2. 把待删的卡打包到 `~/.hermes/arsenal/trim_<时间戳>/cards_backup_*.tar.gz` 再删
3. `h1-reports` 搬到 `/root/archive/72stack-h1-reports`
4. 把 6 张卡名写进 `~/.hermes/config.yaml` → `skills.disabled`（非 Hermes 环境自动跳过）
5. 删旧周快照 / `arsenal.db.bak-*` / `arsenal.findcache.pkl`（`--no-purge` 可跳过）
6. 重建索引 + 跑门禁

跑完必须看到（两种都算成功，只看 `ok`/`tier`，别死记 2204）：

```
# 全量库机器
{"total": 2204, "enabled": 430, "disabled": 1774, ...}
GATE OK（full）· 索引 2204 卡 / 磁盘 2204 张 SKILL.md（递归） | selftest 30/30 | core96 实考 96 条 TOP1 94/96  TOP3 96/96  MISS 0/96 | ...

# 精简库/新克隆机（缺卡，自动降级，不是失败）
{"total": 164, "enabled": 158, "disabled": 6, ...}
GATE OK（portable，157 条基线不适用）· 索引 164 卡 / 磁盘 164 张 SKILL.md（递归） | ...
```

> 你的卡数如果本来就不同（比如还没吸收 2026-10 的批次），数字会按你本地实际算；
> 判断标准是 **索引卡数 == 磁盘 SKILL.md 数**、门禁 `GATE OK`，而不是死记 2204。
>
> **包内带 `skills/.disabled.json`**（导出时从 `config.yaml` 的 `skills.disabled` 生成）。目标机 `arsenal_build.py` 会合并它，复刻「430 启用 / 1774 归档」分层，full 基线才是 `94/96`。不想要这份分层：`export ARSENAL_IGNORE_DISABLED_SEED=1` 再重建。
> 实测缺 seed 的后果：2204 张全算 enabled，`enabled` 加权失去区分度，core 掉到 `88/96 · MISS 2`，两台机器同库不同分。

## 3.5 方式 A+：新机器 / 要 full 基线（一条命令）

仓库里只有 1,168 张（15 伞形 + `domains/` 知识库卡），**不是安装库**。要让一台新机跑出和案卷机一样的 2,204 卡 full 基线，需要 GPG 分享包 + 口令（口令单独私发，绝不进仓库）：

```bash
cd TGSEC-Qtzuu
git fetch origin && git reset --hard origin/master

# 包和口令先放到本机，例如 /root/arsenal-share/
bash scripts/import-arsenal-package.sh \
  /root/arsenal-share/hermes-skills-20261022-1953.tar.gz.gpg \
  /root/arsenal-share/PASSPHRASE.txt
```

它做四件事：**校验包 → 备份旧库到 `skills.bak-<时间>` → 解包到 `~/.hermes/skills`（带 `.disabled.json` 1805 条）→ 装检索栈 + 重建 + 门禁**。
判据只有一条：`gate_last.json` 里 `ok:true` 且 `total == disk`。full 机器应看到 `2204 / 430 / 1774`，`TOP1 94/96 · TOP3 96/96 · MISS 0`。

验收包本身是否干净（换机器前后都能跑）：

```bash
bash scripts/verify_package_clean.sh <pkg.gpg> <PASSPHRASE.txt> 2204 '154\\.219\\.127\\.' secret_literals.txt
# 末行 PKG_CLEAN 才算过；ip_hits / literal_hits 必须 0，seed 必须 > 0
```

自有资产要批量脱敏（目标方 IP 保留，只有自己的 IP/主机名/出口才抹）：

```bash
python3 scripts/redact_own_assets.py --root ~/.hermes/skills \
  --ip-regex '154\\.219\\.127\\.\\d+' --literals-file secret_literals.txt \
  --backup /root/audit/redact-backup --dry-run   # 先 dry-run 看命中，去掉 --dry-run 才落盘
```


## 4. 方式 B：手工（不想跑脚本 / 想看清每一步）

```bash
# 1) 备份
mkdir -p ~/.hermes/arsenal/trim_$(date +%Y%m%d)
cd ~/.hermes/skills/security
tar czf ~/.hermes/arsenal/trim_$(date +%Y%m%d)/cards.tar.gz redteam-*-detail-pack laravel-app-pentest

# 2) 删模板卡 + 重复卡
rm -rf redteam-*-detail-pack laravel-app-pentest

# 3) 胖 refs 搬出技能树
mkdir -p /root/archive
mv 72stack-sec/references/h1-reports /root/archive/72stack-h1-reports
# 顺手改掉 72stack-sec/SKILL.md 里旧路径引用（grep -n 'h1-reports' 72stack-sec/SKILL.md）

# 4) 停用 6 张（Hermes）
python3 - <<'PY'
import sys, json, subprocess
sys.path.insert(0, '/usr/local/lib/hermes-agent')
from hermes_cli.config import load_config
add = ['apple-notes','apple-reminders','findmy','imessage','sdlc-review','teams-meeting-pipeline']
d = list(load_config().get('skills', {}).get('disabled') or [])
new = [x for x in add if x not in d] + d
print(subprocess.run(['hermes','config','set','skills.disabled',json.dumps(new)],capture_output=True,text=True).returncode)
PY

# 5) 清可再生磁盘
rm -rf ~/.hermes/skills/.curator_backups/2026-09-* ~/.hermes/skills/.curator_backups/2026-10-0* ~/.hermes/skills/.curator_backups/2026-10-1[0-3]*
rm -f ~/.hermes/arsenal/arsenal.db.bak-* ~/.hermes/arsenal/arsenal.findcache.pkl

# 6) 装新检索栈 + 重建 + 门禁
cp tools/arsenal/*.py tools/arsenal/*.json ~/.hermes/arsenal/
cp tools/arsenal/arsenal_keeper.py ~/.hermes/scripts/
python3 ~/.hermes/arsenal/arsenal_build.py
python3 ~/.hermes/arsenal/post_rebuild_gate.py
```

## 5. 验收（少一条就是没升完）

| 检查 | 命令 | 通过标准 |
|---|---|---|
| 卡数一致 | `sqlite3 ~/.hermes/arsenal/arsenal.db "select count(*) from skills"` | 与 `find ~/.hermes/skills -name SKILL.md \| wc -l` 相同 |
| 状态 | `... "select status,count(*) from skills group by 1"` | 案卷机 372 / 1774（其他机器按本机实际） |
| 模板卡清零 | `ls ~/.hermes/skills/security/ \| grep -c detail-pack` | `0` |
| 检索可用 | `python3 ~/.hermes/arsenal/skill_find.py "宝塔 面板 密码 忘了" --top 1` | 案卷机命中 `bt-panel-pentest`；无该卡的机器按 §5.1 判 |
| 门禁 | `python3 ~/.hermes/arsenal/post_rebuild_gate.py` | 退出码 0，`gate_last.json` 的 `tier` 为 `full` 或 `portable`（见 §5.1） |
| 全库可达 | `SKILL_FIND_NOLOG=1 python3 ~/.hermes/arsenal/full_reachability_audit.py`（结果写 `/tmp/full_reachability.json`，`REACH_OUT=` 可改；耗时 ~10 分钟） | 案卷机实测 **TOP1 1899/2146（88.49%）· TOP3 2067/2146（96.32%）· TOP10 2122/2146（98.88%）· MISS 24**；这是现状，不是 100% |

### 5.1 库不全的机器（新克隆 / 精简库）——门禁分两层，别把 portable 当 full

`~/.hermes/skills` 的全量卡（案卷机 2146 张）**不入仓**。仓库里的卡是 **1110 张真卡**：`.claude/skills/` 15 张伞形卡 + `domains/` 1095 张知识库卡。`git ls-files | grep -c 'SKILL.md$'` 会报 **1160**，多出的 50 条是 `references/upstream-*-SKILL.md` 这类上游资料转储——文件名以 `SKILL.md` 结尾但不是卡，`arsenal_build.py` 不认，**别拿 1160 跟本机 `find` 数对账**。`docs/learning/*` 被 `.gitignore` 挡住（L51），是**本地脚手架**：里面 283 个符号链接（其中 90 个名为 `SKILL.md`）指向案卷机安装位，案卷机上全部有效、克隆机上悬空；`arsenal_build.py` 跳过悬空项、门禁按「非常规文件」忽略。`scripts/sync-hermes-skills.sh` 只同步那 15 张伞形卡。

所以新克隆机的磁盘卡数是它自己的（常见 100~300 张），**不可能**达到案卷机的检索基线。

门禁从 2026-10-22 起按适用性判定，输出两个层级：

| tier | 含义 | 判定 |
|---|---|---|
| `full` | 本机有全部基线期望卡 | selftest 30/30、三 phase TOP3 满分、core96 TOP3 ≥95% 全量计分 |
| `portable` | 本机缺部分/全部期望卡 | 缺卡条目**显式跳过并记入 `skipped_detail`**；只对「卡在本机」的条目计分，掉一条就 FAIL |

portable 是**诚实结论，不是满分**：它只证明「本机有的卡调得到」，检索质量不可与 full 基线对比。要 full 基线只有一条路——把案卷机的库搬过来（**GPG 包 + 口令私发**，不走明文 rsync）：

```bash
# 案卷机：导出并加密（口令 16 位，另存 PASSPHRASE.txt，绝不进仓库）
bash scripts/export-arsenal-library.sh
gpg --batch --symmetric --passphrase-file /root/arsenal-share/PASSPHRASE.txt \
    hermes-skills-<时间>.tar.gz

# 目标机：一条命令灌库 + 重建 + 门禁
bash scripts/import-arsenal-package.sh /root/arsenal-share/hermes-skills-<时间>.tar.gz.gpg \
    /root/arsenal-share/PASSPHRASE.txt
```

包灌完先跑 `bash scripts/verify_package_clean.sh <pkg> <pass> 2204 '<自有IP正则>' secret_literals.txt`，末行必须 `PKG_CLEAN`。
差异核对只认 md5，不认体积：`bash scripts/export-arsenal-library.sh --diff <manifest.tsv>`。
**不要把 `domains/` 的 1,153 张知识库卡 rsync 进 `~/.hermes/skills`**：那是知识库源，不是策展过的安装库，直接灌进去会污染路由粗排，把 TOP3 拉下来。

## 6. 回滚

```bash
cd ~/.hermes/skills/security
tar xzf ~/.hermes/arsenal/trim_<时间戳>/cards_backup_*.tar.gz
# 6 张停用卡：从 ~/.hermes/config.yaml 的 skills.disabled 里删掉那 6 个名字
python3 ~/.hermes/arsenal/arsenal_build.py
python3 ~/.hermes/arsenal/post_rebuild_gate.py
```

`h1-reports` 回滚：`mv /root/archive/72stack-h1-reports ~/.hermes/skills/security/72stack-sec/references/`，
并把 `72stack-sec/SKILL.md` 里的路径改回 `references/h1-reports/`。

## 7. 坑（都踩过）

- **索引不进仓库**（342MB 二进制）。`git pull` 后必须本地 `arsenal_build.py`，否则你检索的还是旧库。
- **`body_fts` 依赖 SQLite FTS5**：`python3 -c "import sqlite3;sqlite3.connect(':memory:').execute('create virtual table t using fts5(x)')"` 不报错才行。缺 FTS5 的发行版要换自带 sqlite 的 python。
- **别用 `git checkout` 覆盖本地技能树**：仓库只存 15 张伞形卡（`.claude/skills/`）+ `domains/` 知识库树，全量安装卡在本机；从仓库同步的方向是 repo → 本机伞形卡，不是本机 → repo。`domains/` 也别往 `~/.hermes/skills` 里灌，见 §5.1。
- **门禁的 full 基线只属于全量库机器**：新克隆机拿到的 `tier=portable` 不是失败，`skipped_detail` 会列出每条不适用基线；portable 却冒 ✗ 才是真问题（卡在本机却调不到）。
- **`skills.disabled` 是 1805 条不是 6 条**：这是全量停用名单（原本 1799），别把它当增量表去覆盖。
- **删卡前必须备份**：本仓库不再包含那些卡，删了只能从 `trim_<时间戳>.tar.gz` 恢复。
- **门禁第一次跑会建基线**（`gate_state.json`），第二次起才比对「新增/改动卡」；别把首次的「新增 N 张」当报错。
- **评测/门禁/selftest 一律带 `SKILL_FIND_NOLOG=1`**，否则污染 `query.log`（真实检索统计）。
- **重建期间别并发检索**：`arsenal_build.py` 会重建表，检索进程可能读到半成品（本机 keeper 已串行化，手工跑注意）。
- **磁盘余量 ≥1G**：重建时旧库 + 新库会短暂并存。
- **`tools/arsenal/` 必须整目录拷，别只拷三个主脚本**：`arsenal_build.py` 会调同目录 `build_termdf.py`（缺了 `term_df` 表，门禁判硬伤），门禁会调 `selftest.py`、评测会调 `route_eval.py`；升级脚本已按 `*.py` 全拷。

## 8. 给 AI 的提示词（复制即用）

```
你正在使用 TGSEC-Qtzuu 旧版技能库。请升级到 2026-10-22 版：
1) cd 到仓库目录，git pull origin master
2) bash scripts/apply-arsenal-20261022.sh
3) 如果脚本不存在或失败，按 docs/UPGRADE-20261022-ARSENAL.md §4 手工执行 6 步
4) 验收：索引卡数 == 磁盘 SKILL.md 数；post_rebuild_gate.py 退出码 0，gate_last.json 里 tier=full 或 portable
   （portable=本机缺基线卡，属正常；但 skipped_detail 之外冒 ✗ 就是真问题，别忽略）
5) 报告：删了几张卡、停用几张、索引卡数、门禁 8 项结果、索引体积和重建耗时
不允许跳过重建索引；不允许把 use_count=0 当删卡依据；不允许把全量技能卡提交进仓库。
```
