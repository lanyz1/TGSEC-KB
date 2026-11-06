# 批次收口与仓库呈现（2026-10-06 实录）

场景：报告包（报告.zip，29 成员 → 14 案 / 22 课 / 5 技能补丁）吸收批次推送后的收尾——① 推待定勘误 commit；② 用户要求「UPDATE-*.md 不要在仓库显示」。两条都在当轮落地（远端=本地零漂移）。

## 1. UPDATE-*.md 归档 docs/updates/（用户指令）

处置：**归档而非删除**（保留历史；用户只要求「不显示」。若要连存档都清掉用户会明说）。

配方：

1. `git mv UPDATE-2026-*.md docs/updates/`（保留 rename 历史）。
2. 全库列引用：`grep -rln 'UPDATE-2026-' --exclude-dir=.git .`（实测 4 文件 17 处：README 10 / START 6 / MASTER 1 / INGEST 1）。
3. 两种形态同步替换：
   - 链接：`](UPDATE-2026-` → `](docs/updates/UPDATE-2026-`
   - 散文：`根目录 `UPDATE-` → ``docs/updates/UPDATE-``（README 维护约定行、START「看更新」行、INGEST 指针行）
4. **排除 `docs/updates/` 内文件自身**：互相引用是兄弟相对路径，平移后天然正确；全局替换会把它们改成 `docs/updates/docs/updates/...` 死链。
5. 校验（全部要 0 残留 / 逐条真）：
   ```bash
   grep -rn '](UPDATE-2026-' --include='*.md' . | grep -v 'docs/updates/'   # 0
   grep -rn '根目录 `UPDATE' --include='*.md' .                              # 0
   # 对每个 ](docs/updates/UPDATE-*) 目标逐个 os.path.exists 验证
   ```
6. commit + push；`git ls-remote origin refs/heads/master` == `git rev-parse HEAD`；工作树 0 脏。

**今后约定**：新 UPDATE 文件直接生成在 `docs/updates/`；根目录只留核心面（README/START/MASTER 等）。

## 2. 「一起推」流程

- 待推 commit（如勘误）先汇报清楚；用户「一起推送到仓库啊」= 放行，且是**把当时全部待推 commit 一次性 push**（本轮实测：勘误 f5a28386 + 归档整理 commit 合并一推 `cee95569..220a58f4`）。
- 推后核对：`git ls-remote origin refs/heads/master` 与本地 `git rev-parse HEAD` 哈希一致 + 工作树干净。
- 用户贴的仓库页截图 commit 信息疑似过期时（浏览器缓存），以 `git log`/`ls-remote` 事实为准，别把文件重改一遍。

## 3. 蜂群吸收收口验证三件套

子代理并行吸收后必做（本轮终检 12/12 有落点）：

1. **关键词 battery**：把蜂群摘要里出现的每个案子/系统名/技能名做成列表，逐个 `grep -rln <kw> domains/ docs/ scripts/`——必须每项有落点，缺的补。
2. **技能补丁持久化**：逐条 `grep` 补丁段落（如 venom-hydra 的「MINER HUNTER」段、php-disable-functions 的「FCGI sock」段），确认已写盘。
3. **git 终态**：树干净、本地==远程零漂移。

## 4. 「假矛盾」裁定（SUNNIC 实录）

复核报「案卷两处矛盾」→ 别直接翻案改原文，先取一手证据：

- **源站 IP 两个版本** → 读 `stolen_tokens.log` 心跳时间线：`.197` 仅 7 条（10/4 上午 10:50 前），11:30 起全切 `.188`（ws-vm-260822，170 条到 10/5 15:50）= **运营方中途轮换基础设施**，两版都真实。教训：打前必须重新解析 IP。
- **SSRF「成立 vs 不成立」** → 端点区分：`.domain-monitors/` 服务端 fetch（真 SSRF，早期靠它捕源站 IP）vs 充值审核流（不 fetch，吃审核员浏览器 = CSRF 面）。两个不同面，不矛盾。

处置：结论写成**勘误段进 `sunnic-agent-saas/meta.md`**（不动原文）+ 单 commit 待推。

## 5. 延迟到达的蜂群回执

若批量回执晚到或正文不完整——全文始终可从 `/root/.hermes/cache/delegation/`（`subagent-summary-*.txt` + `live/deleg_*/` 日志）捞出来消化（本轮实测有效），捞完做第 3 节三件套终检即可，别重跑子代理。
