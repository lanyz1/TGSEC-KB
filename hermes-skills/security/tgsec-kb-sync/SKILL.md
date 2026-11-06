---
name: tgsec-kb-sync
description: Use when syncing or diffing the TGSEC knowledge base.
---

# TGSEC 知识库：上游同步 / 本地差距对比

本地知识库 = `/root/security-suite`（TGSEC-Qtzuu 克隆）+ `~/.hermes/skills/security/`（实际生效的技能）。
本技能管的是**这两个目录与上游仓库之间的一致性**，不是渗透本身。

## 0. 先定方向，别猜（最高优先）
- 「同步」有两个相反方向：**repo→本地**（刷新本地技能/知识库）与 **本地→上游**（把本地经验提交回仓库）。用户一句「同步更新仓库的配置」歧义极大 —— **先用一句话确认方向**再动手，否则整轮白干。
- 对比类请求（「本地有什么仓库没有的」）先交**清单**，落盘/上游动作等用户点头。
- 上游是公开仓（`https://github.com/lanyz1/TGSEC-Qtzuu`），但没有凭据 → **推不了**；要交付上游用 `git format-patch` 出补丁文件给用户提交。

## 1. 上游侦察（写任何东西之前）
```bash
cd /root/security-suite && git fetch origin
git log -1 --format='%h %ad' --date=short origin/master   # 上游最新
git log -1 --format='%h %ad' --date=short HEAD            # 本地快照
git rev-list --count origin/master..HEAD; git rev-list --count HEAD..origin/master
git ls-tree --name-only origin/master                     # 顶层结构，以此为准
git ls-tree -r --name-only origin/master | grep -c 'SKILL.md'
```
- **上游会重构目录**：技能已从 `hermes-skills/` 搬到 `.claude/skills/`。一律以 `git ls-tree` 的**实际结果**为准，**不要信 AGENTS.md、README、脚本注释里的旧路径**。
- 不动工作区就读上游：`git worktree add /root/tgsec-latest origin/master`，读完 `git worktree remove <path> --force`。
- 判定是否已分叉：双方各有独有提交 = 历史被重写过 → 见 §3。

## 2. 动手前先备份
```bash
mkdir -p /root/skillbak
tar czf /root/skillbak/security_skills_$(date +%Y%m%d_%H%M).tar.gz -C /root/.hermes/skills security
```
- 旧 clone 的未跟踪本地件也要留：`git status --porcelain | awk '$1=="??"'` → 拷进 `/root/skillbak/old_clone_untracked/`。
- 备份**不得**放在 `~/.hermes/skills/` 下：`skill_view` 的裸名解析会 rglob 整棵树，`security.bak.*/<name>` 会被判成 Ambiguous（上游脚本自己也这么警告）。

## 3. clone 脏了：重建，别硬合
- 上游**重写过历史**（或做过内容净化）时，旧 clone 的 `.git` 里**仍留着上游已撤掉的历史**（泄漏面）—— 直接删掉重克隆，不要 `pull`/`merge`/`rebase`（分叉后 `--ff-only` 永远失败）。
- 先摘工作树再删：`git worktree remove /root/tgsec-latest --force` → `rm -rf /root/security-suite` → `git clone --depth 1 <url> /root/security-suite`。
- `--depth 1` 浅克隆够用（实测 288M vs 完整 855M），后续 `git pull` 照常。

## 4. 技能灌进本地（overlay）
```bash
cd /root/security-suite
grep -n 'SRC=' scripts/sync-hermes-skills.sh scripts/sync-agent-skills.sh
sed -i 's#\$ROOT/hermes-skills#$ROOT/.claude/skills#; s#\$SUITE_DIR/hermes-skills#$SUITE_DIR/.claude/skills#' scripts/sync-hermes-skills.sh
bash scripts/sync-hermes-skills.sh          # overlay：覆盖同名，保留私有
```
- **脚本会静默失效**：`SRC` 指向已不存在的目录时它打印 `[!] missing … repo incomplete` 然后 `exit 1`，**一张技能都不装**却像跑完了。改完 SRC 必须重跑并核对（§5）。
- 默认 overlay = 不删本地私有技能（要的就是这个）；`--prune` 会删，一般别用。
- 技能在**会话启动时加载**，落盘后下个会话生效。

## 5. 验证：看方向，不看数量
```bash
bash ~/.hermes/skills/security/tgsec-kb-sync/scripts/verify-skill-sync.sh [仓库路径]
```
- `Only in ~/.hermes/...` = 本地私有增量 → **正常，保留**。
- `Only in <仓库>/...` = **真失败**（没灌进来）→ 必须处理。
- 技能总数**不变也可能是对的**（仓库 15 + 私有 21 + README = 37）—— 逐张 `diff -rq`，**不要用计数当成功证据**。

## 6. 别碰：仓库的 Hermes 记忆配置
- `ai-config/hermes/setup.sh` **不要盲跑**：它 `cp` 覆盖 `~/.hermes/memories/MEMORY.md` / `USER.md`，会冲掉本地积累的实战情报（实测本地记忆是仓库通用模板的超集）。要合就 diff 后**选择性并入**。
- 同理，仓库同步来的技能（`tgsec-suite`、`pentest-execution`、`security-kb-ingest` 等）**下一次同步会被覆盖** → 本地工作流经验不要写进这些 SKILL.md，写在私有技能里。

## 7. 差距对比：仓库缺什么（grep 有坑）
- 按**内容**判，不按文件名判。案例名出现在 `domains/*/case-lessons/` ≠ 有可执行的技法卡。
- 关键词计数**会被字典/词表污染**：`DBX` 命中的是密码字典、`算力` 命中的是比喻用法、`snapshot` 命中的是无关上下文。**宣告「仓库没有 X」之前必须看命中样例**：
```bash
git grep -i -F "关键词" origin/master | head -12 | cut -c1-165
```
- 结论分两档：**内容级 0 命中**（真缺）vs **有案例名、无技法卡**（半缺）。两者在报告里必须分开写。
- 仓库若声明「只收提炼层、原文全文不入库、必须脱敏」（AGENTS.md §3.2）：本地留全量，往上游提交前先脱敏提炼。

## 8. 交付「本地独有经验」
- 打成 zip + `README_索引.md`：逐条列技能卡（名 + description）与 references（名 + 大小），并**写明对比基准 commit**。
- 用 Python `zipfile` 遍历目录打包（`zip` 二进制不一定装），`os.path.relpath` 保留结构。
- 发送用 `MEDIA:/绝对路径`；大件先算体积（技能卡通常几百 KB 级）。

## 9. 收尾
- 更新 MEMORY 里知识库那一条：新 HEAD、技能目录（`.claude/skills/`）、同步脚本已修、私有增量位置。
- 报告只写**验证过的数字**（逐张 diff 结果、磁盘变化、克隆体积差），别只报「已完成」。

## 10. 净化复验：强推 ≠ 把泄漏清干净

上游（或自家仓）做过「撤全文卷 + 全史重写 + 强推」后，**不要采信它的自报复扫结论**，按托管侧实测：

- **旧提交在 GitHub 上仍可被匿名取用**，三条口都通：`/commit/<sha>.patch`、`/archive/<sha>.tar.gz`（整包）、`raw.githubusercontent.com/<owner>/<repo>/<sha>/<任意路径>`。而 `api.github.com/.../git/commits/<sha>` 会返 **404** —— 用 API 判「旧对象已回收」必错；判据取 `.patch`（骗不了人）。父提交同样要探（链不会只残留一个）。
- **私有期净化 + 之后转公开 = 窗口**：私有仓的悬空对象外网取不到，一转公开同一批对象就成了匿名可下。查第三方副本看 API 里的 `forks_count` 与 `web.archive.org/web/2026/<repo-url>`。
- **量化「到底泄了什么」**：把旧归档下来解包，扫遗留的报告卷 → 常见 `sk-` / `tga_`·`tgb_` / bot token / 口令字面量 + 手机号/身份证。**命中只报 [类别 / 文件 / 行号 / 长度]，值绝不打印**（聊天记录本身就是泄漏面）；`secret-patterns.md`、CVE PoC 文档里的示例串、`uv.lock` 哈希是已知误报，结论分「示例串 / 真凭据」两档。
- **修法只有两条**：删仓重建（推一个**已验不含旧对象**的干净镜像：`git cat-file -e <旧sha>` 失败 + `ls-tree -r | grep -c case-reports` 为 0），或请托管方 Support 回收不可达对象。**再强推一次没用。**

命令、扫描器写法与报告形状见 `references/repo-history-purge-verification.md`。

## 支持文件
- `references/repo-history-purge-verification.md` — 托管侧旧对象探测（三条口 + API 假 404）、第三方副本检查、泄漏量化扫描器的写法与误报清单、干净镜像验收与删仓重建流程
- `scripts/verify-skill-sync.sh` — 逐张对比仓库 `.claude/skills/` 与 `~/.hermes/skills/security/`，打印**仓库独有/本地独有**方向；仓库独有非 0 即失败。
