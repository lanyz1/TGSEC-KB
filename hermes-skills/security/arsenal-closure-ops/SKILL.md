---
name: arsenal-closure-ops
description: Use when 吸收/复盘收尾：重建索引→检索验证→案例课→发布。
---

# arsenal-closure-ops — 技能库收尾闭环

外部包吸收完、战后复盘回写完、新建或拆分技能卡之后，都要跑这套收尾。
**落盘 ≠ 交付**：只 patch 技能卡不重建索引，新卡根本检索不到，等于白加。

## 六步闭环（缺一步主人会问「ops 还差吗」）

### 1. 军械库重建三连

```bash
cd /root/.hermes/arsenal
python3 arsenal_build.py    # total 应 = 原数 + 新增卡数
python3 vuln_build.py       # entries 递增 + zero=true
python3 selftest.py         # 路由回归应 30/30
```

参考基线（2026-10-23）：arsenal 2,225 张（enabled 451 / disabled 1,774 / legacy 1,856）；vuln 8,007 条；selftest 30/30。

基线只作**量级对照**，别当目标值背：以 build 输出的 JSON（`total/enabled/disabled/legacy/bytes`）为准，和上轮差 1~2 张是正常归档卡增删。
口径提醒：`find ~/.hermes/skills -name SKILL.md` 会把 `.archive/` 下的归档重复卡算进去，build 不算 ⇒ **find 比 db 多 2 是正常的**（本库实测 2227 vs 2225），别把口径差当“没同步”。

### 2. 实测检索命中（别凭「应该能搜到」）

```bash
python3 /root/.hermes/arsenal/skill_find.py "<新卡关键词>" --phase recon
```

- ⚠️ **看完整 hits 列表，别 `head -6`** —— 实测新卡排在**第 2 位**，被 head 截断后误判成「没进索引」，白折腾一轮
- `[E]` = enabled → 直接 `skill_view(name)`
- `[D]` = 禁用归档 → 走该行 `load:` 给的 `catalog` + `references/legacy/<卡名>.md`
- 新卡描述太素时会被归档老卡压分：把关键词（产品名/症状/手法名）写进 description 与正文首段即可上浮

### 3. 案例课回写

TTP 进技能卡解决的是「知道怎么做」；同面开打时还需要 case 才能「看过别人怎么做」。

- 位置：`TGSEC-Qtzuu/domains/<面>/case-lessons/<slug>.md`
- 格式：**一句话 / 链 / 判据表 / 边界坑 / 检查清单**
- case 与 TTP 分工：技能卡写可复用打法，案例课写这一场的完整攻击顺序与死路
- 原文全文不入库；凭据/PII 一律 `[REDACTED]`

### 4. 索引计数用实数

```bash
cd /root/TGSEC-Qtzuu
find domains -path "*/case-lessons/*.md" ! -name "README.md" | wc -l
```

各域 `README.md` 会混进口径——实测把 142 篇写成 143（含 README 的口径）。CASE-INDEX 头部计数、增补日期、末尾表格三处要同步改。

### 5. 推前扫敏感串

用 `search_files` 工具跑：`tga_|tgb_|BEGIN (RSA|OPENSSH) PRIVATE|sk-[A-Za-z0-9]{20}`。
复杂内联 grep 正则会触发 hardline 拦截——写成脚本或用 `search_files`，别在 terminal 里硬拼多分支正则。

命中先看是不是**方法论/检测规则文本**（如 dork 词表里的 `BEGIN RSA PRIVATE KEY` 字符串），那不算泄露。

### 6. 定向 add + commit（push 必须主人点头）

```bash
git add <本次改的每一个文件，逐个列名>
git commit -m "ingest: <批次> -> N case-lessons; CASE-INDEX a->b"
git log --oneline -1        # 停在这里
```

**推送闸门（2026-10-23 事故后立规）**：收尾时自作主张 `git push origin master`，被主人当场喝止「你别瞎几把给我推送到仓库了啊，没有我的同意别推」。TGSEC-Qtzuu 是公开仓，push = 对外发布，撤回也要再推一次。

- 默认止于本地 commit；要推先问一句「要不要推？N 个文件 + commit 短哈希」
- 只读预演随时可跑：`git push --dry-run origin master`
- 主人说「保持现状」= 不 push、不 revert、不 reset；本地领先 origin 是合法状态
- 已经误推：先摆事实（commit / 文件数 / 有没有敏感串 / 远端现状），给软撤 revert 与硬撤 force-push 两条路，等指令，不自行补救

- **`git add .` 禁止**：工作区常年有 `docs/playbooks/`、`docs/learning/` 类历史残留，一把 add 全推上去
- 提交完核对 `git log --oneline -1`（推不推由主人决定）

## 7. 舰队对齐（多机同步）与“假吸收”验收

推完 worker 之后，**rsync 的“sent”不代表落地**（本次 rsync 全报 banner exchange timeout，实际都没同步上）。验收只认 md5 清单：

```bash
# 本地
cd /root/.hermes/skills && find . -name SKILL.md -exec md5sum {} + | sort -k2 > /tmp/loc.md5
# 远端（-p 按实际端口）
ssh root@<host> "cd /root/.hermes/skills && find . -name SKILL.md -exec md5sum {} + | sort -k2" > /tmp/rem.md5
# 三件套：缺卡 / 多卡 / 同路径不同 md5
```

- 远端只需传**卡片文件**，索引让它自己 `arsenal_build.py` 重建（别传 db，路径/版本容易对不上）
- SSH 连不上先查“是不是同一台多宿主”：`hostname -I` 一次把全部 IP 吐出来。本次目标 45.192.102.149 死活连不上，实为同一台机器的另一网段地址（154.219.127.31:2222），rtt 0.28ms 就是线索——**别因为 22 被 filtered 就判定主机死**
- **对齐结论是快照，不是状态**：报「已全等」前当场重跑 md5 差集。两次报数之间别的会话/worker 还在写卡——上一轮报 2,227/2,227 全等，本轮重跑变 2,228 且缺 `host-implant-triage`，旧结论直接作废。交付一律给「卡数 + 缺/多/内容差三行」，别复述上一轮
- **`git pull` 不代表技能库同步**：仓是 `domains/` 知识库，技能在 `~/.hermes/skills`，两条独立通道；仓齐看 `HEAD == origin/master` + `dirty=0`，库齐看 md5 三行 + 重建后的索引 `total`
- **拿更新仓库的那几台当跳板 = 违纪**（2026-10-23 主人明令「我给你更新仓库的那3台服务器也不能当跳板机」）：不 `ssh -J` / 不 `ProxyJump` / 不起 SOCKS 与端口转发去连第三台；要连别的机器直连。自查 `grep -nE 'ProxyJump|ProxyCommand' ~/.ssh/config`、`pgrep -af 'autossh|chisel|frpc|ssh -[DLNR]'`

**假吸收验收**（案卷自称“已写入 references/xxx.md”不算数）：
1. `ls` 那个被引用的路径，不存在 = 没吸收
2. 全库 grep 目标 token（域名/案子名）与**手法指纹**（接口名、参数名、框架名）
3. 两个都命中才算真吸收；只命中通用手法卡 = 按形态吸收、按目标没留名，是正常形态但要说清楚

详见 `references/fleet-parity-and-absorption-audit.md`。

## 交付账本要含

重建后张数 / vuln 条数 / selftest 结果 / 新增课名单 / CASE-INDEX 前后值 / commit 区间。

**报账时说清「还差什么」**：能自动化的都跑完；剩下的只有人工选择项（清原件、清未跟踪文件），一句话列出来让主人决定，不要自己擅自删。

## 反模式

- ❌ 吸收完只回一句「已落位 35 处」，不重建索引 → 新卡等于不存在
- ❌ 拿 `head -6` 的检索结果下结论
- ❌ **拿案卷自述当吸收证据**：案卷写“已新增 references/xxx.md”但文件不存在（本次实测 tw5500 那条全库 0 命中），属于假吸收；验收必须 `ls` 路径 + 全库 grep 双证
- ❌ 拿 `find` 的卡数直接和 db 比（差 2 就是 `.archive/` 口径，不是掉卡）
- ❌ 手算课数（139+4=143），不跑 `find`
- ❌ 用 `git add .` 收拾工作区
- ❌ 把「要不要清原件/清残留」也当成待办拖着 —— 明确抛给主人一句话
- ❌ 没问就 `git push`（公开仓 = 对外发布；「保持现状」连撤回也一并禁止）
- ❌ 把上一轮的「已全等」当现状复述（库一直在长，报数前重跑差集）
- ❌ 借更新仓库的那几台机器当跳板/隧道（主人明令禁止）
