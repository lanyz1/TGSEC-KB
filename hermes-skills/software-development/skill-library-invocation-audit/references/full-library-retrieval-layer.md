# 全库检索层：让 1,799 张归档卡在实战中可调用

2026-10-21 实测。目标不是压索引，而是让 **2,173 张卡（含 1,799 张禁用归档）** 在实战中能被查到、加载、执行。

## 组成

| 文件 | 作用 |
|---|---|
| `/root/.hermes/arsenal/arsenal_build.py` | 遍历全部 `SKILL.md`，解析 frontmatter、启用状态、legacy 路径、标题、摘要，写 `arsenal.db` |
| `/root/.hermes/arsenal/skill_find.py` | 查询、打分、阶段过滤、深搜，输出状态 + load 命令 + `body_path` |
| `/usr/local/bin/skill_find` | shell 包装，直接 `skill_find "..."` |
| `/root/.hermes/arsenal/selftest.py` | 30 条实战问句路由回归 |
| `/root/.hermes/arsenal/fix_legacy_paths2.py` | 给 legacy 卡插入原目录提示（幂等） |

## 数据模型

每张卡一行：`name`、`description`、`tags`、`category`、`status`、`catalog`、`legacy`、`path`、`headings`（全文所有 `##`/`###` 标题）、`excerpt`（正文前约 4K 字符）、`body_path`、`use_count`。

- 启用卡：`body_path` = 原 `SKILL.md`。
- 归档卡：`body_path` = `<目录卡>/references/legacy/<旧卡名>.md`；`catalog` 必须非空且文件存在。
- `enabled` 数据库计数（本次 372）包含平台限定/未进索引卡；常驻索引是 360，两个数字不要混。

## 检索算法

1. 查询词拆分；中文长词补 2 字 bigram；维护产品/缩写同义词（s3↔oss、k8s↔kubernetes、ruoyi↔若依、jenkins↔ci/cd 等）。
2. 先算文档频率 `df`，`idf = log((N+1)/(df+1)) + 0.5`。
3. 命中权重：卡名 100、描述 45、标签 40、标题 25、摘要 8；多词覆盖加分；阶段匹配只加约 20。
4. 默认对 Top 80 候选读全文，按词频补分；`--fast` 跳过。
5. 输出按分数排序，附 `[E]`/`[D]`、命中字段、`load`、`body_path`。

**为什么不用 FTS5 trigram**：SQLite trigram 对 2 字中文词（注入/若依/未授权）匹配不到；本机用 Python 字面量包含匹配，`headings` 覆盖正文深处的小节名，稳定且够快。

**IDF 的必要性**：没有 IDF 时，通用词“未授权”会在大量卡里命中，把 `monitoring-plane-unauth-recon`（Grafana/Prometheus）这种产品卡挤出 Top5；加 IDF 后产品名压过泛词。

## 归档卡的相对路径

legacy 副本在 `<目录卡>/references/legacy/<旧卡名>.md`，但卡内 `references/...`、`scripts/...`、`templates/...` 相对**原目录**。每张 legacy 卡在 frontmatter 闭区间后插入：

```markdown
> 归档卡：原目录 `/root/.hermes/skills/security/<旧卡名>`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('<原目录>/…')`，不要相对 `references/legacy/` 解析。
```

**踩过的坑**：legacy 文件开头有 `<!-- archived from ... -->`，若只判断 `startswith('---')` 会走 else，把提示追加到 EOF，等于没加。必须正则找 frontmatter 的 `^---$` 开/闭区间，插在闭区间后；`fix_legacy_paths2.py` 已幂等。

实测：213 张 legacy 含 883 个相对链接，35 个原目录文件本就缺失（历史遗留），不要伪造；其余按原目录可读。

## 验收

```bash
python3 /root/.hermes/arsenal/arsenal_build.py
python3 /root/.hermes/arsenal/selftest.py
```

- `total=2173 enabled=374 disabled=1799 legacy=1856`；1,856 张 legacy 全部有 catalog + body_path，0 缺失。
- `selftest.py` 30 条实战问句 Top5 命中 30/30（ADCS、Nacos、phpMyAdmin、Shiro、Grafana、S3、JWT、FastAPI、WordPress、Telegram 等）。
- 抽样实弹：`skill_view(name='security-archive-index', file_path='references/legacy/adcs-certipy-attack.md')`、`skill_view(name='java-audit-pipeline', file_path='references/legacy/druid-console-unauth.md')`、`recon-for-sec` 的 `hunt-subdomain` 均能出全文。
- `skill_view` 的 `file_path` **必须带 `.md`**；不带后缀只返回目录条目。
- 返回 `[SKILL_PRUNED]` 时，用 `skill_find --json` 的 `body_path` 直接 `read_file`。

## 反模式

- 把 1,799 张全部解除禁用：索引回到 183KB，模型在 2,000+ 行里更选不中，反而更用不到。
- 把索引字节数/禁用数量当 KPI：这是 token 视角，不是实战视角。
- 用卡内正文的历史数字当库存：以 `arsenal.db`/脚本输出为准。
