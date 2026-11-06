## 巨型 SKILL.md 分册（历史 >200KB 字节；现行按 >15K 字符）

判定：旧口径按字节，单卡 **>200KB** 可能读爆；**现行按字符**：`len(text) > 15,000` 就拆，>20,000 字符的全文再分片（见下 ★）。2026-10-17 拆前的 5 张：`sinian-omnipotent` 728KB、`offensive-windows-boundaries` 568KB、`offensive-windows-mitigations` 531KB、`offensive-crash-analysis` 410KB、`offensive-basic-exploitation` 355KB。

拆法（保留语义、零删改）：

1. 先备份：`tar czf /root/skill_backup_<date>.tar.gz -C /root/.hermes skills`。
2. 解析 frontmatter，按 `^## ` H2 块切分；保留 frontmatter + 开头 Metadata/Overview/Instructions，其余按 **≤12K 字符**（不是 12KB 字节；中文约 36KB 字节）分组写入 `references/part-XX.md`（文件名用标题 slug）。重卡宁可多几片，别让单片再读爆。
3. SKILL.md 末尾加 `## 分册索引（按需加载，不要一次全读）`，逐条 `[标题](references/xxx.md) — N KB`。
4. 目标 SKILL.md **≤12K 字符（约 20–36KB 字节，视中英比例）**；本次 5 张降到 21/4/14/10/3 KB 字节，refs 9/9/9/7/8 份。

**★致命坑（本次踩过）**：不要拿「已经拆过的 SKILL.md」再跑第二遍分册——第一遍已把大块搬进 references，第二遍只看到剩余小块，重建时会把这些块删掉。`offensive-crash-analysis` 因此丢了 Day1–6 约 290KB。正确做法：**每次分册都从备份 tar 里的原卡重新开始**，或第一遍就一次成型。

验证（必须全绿）：

- 原卡每个 H2 块的规范化文本，在新 SKILL.md + refs 的 H2 块池中做 **Counter 等值比较**；比较时 `rstrip` 尾随空白，否则短块会假阴性。输出 `missing=0 / extra=0`。
- 每个块恰好出现一次（防重复/防丢块）。
- `yaml.safe_load(frontmatter)` 通过。
- `skill_view(name)` 返回的 `linked_files.references` 数量与磁盘一致；实测 `offensive-basic-exploitation` = 3KB + 8 个分册，`sinian-omnipotent` = 23.5KB + 9 个分册。

可直接复用脚本：`scripts/split_oversized_skill.py`（从原始 SKILL.md 一次分册 + 逐块校验；检测到已拆分默认拒跑，先备份再跑）。完整实测账见 `references/context-budget-and-oversized-cards.md`。

### ★按字符不按字节（2026-10-21 血坑）

`skill_md_bytes`、`os.path.getsize()` 都是 **UTF-8 字节**；中文约 3 字节/字符，**12KB 字节预算只够约 4K 字符**。本次第一版按 30KB 字节选目标、按 12KB 字节切，结果 `cloud-security-pentesting`（68.5K 字符）被切成 1.2KB 空壳路由，而 ASCII 重卡（26.7K 字符）因字节数不到 30KB 完全漏拆。

- 选目标：`len(open(path).read()) > 15000`（字符），不要用 `skill_md_bytes > 30*1024`。
- 切预算：**12,000 字符**（不是 12KB 字节）；启用卡目标 ≤15K 字符。
- 全文二次分片：`full.md > 20,000 字符` 才切；片预算同样 12,000 字符。
- 第一节本身超预算时，在 `###` 或编号列表项边界再切一刀；否则只留 1KB 引言，路由卡等于废了。

### 索引分片（目录 index >20KB）

`references/index.md` 超过 20KB 后，按 `- **name**` 条目顺序切成 `index-part-01.md`…（每片 ≤12KB 字节），master `index.md` 只留片名+首尾条目+条数。**重分片会删掉旧字母片**，目录卡 MERGED-INDEX 块里的 `index-a-c.md` 必须同步改成 `references/index.md`，否则块内指针全断。验收：master 片数合计 = `## 归档子卡（已合并 N 张）` 的 N；全库条目 0 重复、每条 `references/legacy/*.md` 存在。

### full.md 二次分片（>20K 字符）

`references/full.md` 本身仍可能是 86K 字符；按 `## ` 打包成 `references/parts/part-01.md`…（≤12K 字符/片）+ `parts/index.md`（节名→片路径）。**不重写原 nav 列表**，只在末尾追加“全文较大，已分 N 片，先读 parts/index.md”；保留 `full.md` 整包。单节 >12K 时独立成片，别在片内硬切代码块。

