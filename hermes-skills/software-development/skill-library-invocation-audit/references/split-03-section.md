## 上下文预算体检（回答「技能太多会不会调不到」）

先分清三种「调不到」：

1. **名字不在索引** → 裸名撞名/被覆盖（见四件套第 2 条）。
2. **名字在，但单卡读爆上下文** → 巨型 SKILL.md（见下节）。
3. **加载过又被压缩剪掉** → `[SKILL_PRUNED]` 不是加载失败；按名重载即可。

实测命令：

```bash
/usr/local/lib/hermes-agent/venv/bin/hermes prompt-size --json
```

看 `system_prompt.chars`、`skills_index.chars/bytes`、`tools`、`sections`。2026-10-17 实测：system 196,869 chars；skills index **181,063 chars / 248,802 bytes**；security 一类占 **171,056 chars（95%）**；模型窗口 200,000。按中英混合估算索引约 **6.7–8 万 token**，占窗口 1/3。

2026-10-21 复测（同一台）：2,157 张；索引 **183,732 chars / 251,615 bytes**；system 199,596 chars；security **2,042 张 / 231.7 KB**，其余 115 张。索引**没有被截断**——`prompt_builder` 全量拼入、无 budget cap；所以「后面的卡看不见」是伪命题，真正丢的是正文。`--json` 的 `skills_breakdown[]` 带 `index_line_total_bytes` 与 `skill_md_bytes`，可直接按家族/单卡算账。

2026-10-21 合并+拆卡后（阶段值；最终口径见下节）：**2,157 → 361 张启用**（359 进索引，2 张平台限定），索引 **38.6KB**，system **46,919 chars**（-76.5%）；1,799 张 disabled，正文全量复制进 16 张安全域目录 + `general-archive`（共 17 张目录卡）的 `references/legacy/`。60 张超长卡已拆主卡+全文，18 张全文再分 62 片，索引 59 片。执行细节见 `references/library-merge-playbook.md` 与 `references/megacard-split-and-index-shard.md`。

### ★实战可调用层（2026-10-21 第二轮，用户纠偏）

用户明确纠正：**不要再用“索引缩小/禁用数量”当验收；目标是每一个吸收过的手法在实战中能被查到、加载、执行。** 为此在合并之上加了一层全库检索，不再靠常驻索引赌模型选得中：

- `arsenal_build.py` 把 **2,173 张**（以 `arsenal.db total` 为准；2026-10-21 最新重建 enabled=374）的 name/description/tags/headings/excerpt/body_path 写进 `arsenal.db`；归档卡用 legacy 全文做 body。
- `skill_find.py`（`/usr/local/bin/skill_find`）按目标栈/症状/阶段检索，输出 `[E]`/`[D]` + 精确 `skill_view` 命令；`[D]` 形如 `skill_view(name='<目录卡>', file_path='references/legacy/<卡名>.md')`。
- **中文检索坑**：SQLite FTS5 trigram 匹配不了 2 字中文词（注入/若依/未授权），改用 Python 字面量匹配；IDF 加权防止“未授权”这类泛词把产品卡挤出 Top5（Grafana 实测输过通用卡）。
- **归档路径坑**：legacy 文件开头的 `<!-- archived ... -->` 会让 `startswith('---')` 误判；提示必须插在 YAML frontmatter **闭区间之后**，追加到 EOF 等于没加。卡内 `references/scripts/templates` 相对**原目录**，不是 legacy 目录。
- **吸收坑（2026-10-21 审计）**：`skill_merge.py` 只把 `SKILL.md` 文本写进 legacy，不复制 `scripts/`、`templates/`、`assets/`、数据目录。194 张 `pack: survey-skill` 卡中 145 张没有任何脚本；317 个 `docs/learning/*` 历史路径中 284 个已由 `resolve_asset_paths.py` 建立同名牌 symlink 兼容层，20 个索引/状态/模块页由 `consolidate_assets.py` 生成，剩余 6 个是无本地对应卡的缺源卡；90 个 tar/zip 归档对当时 109 个缺失 ops 名命中 0（彻底回滚后余 106 个）。之后已从 `hi-fullhouse/cybersecurity-skills` 整目录补回 39 模块 / 195 技能，`css_query` 恢复。以后吸收必须整目录落地并跑 `python3 tools/ops/absorption_audit.py`，记录 `source/sha256/license`；只拿到文本的卡标 `asset_status: text-only`。完整证据、来源分布与未来吸收清单见 `references/absorption-provenance-audit.md`。
- **可调用性（2026-10-21 收口）**：`callability_gate.py` 对 154 个 ops 脚本做编译 + 入口 `--help`，结果 **152 ready / 2 library / 0 manual / 0 broken**；adapter 薄封装按目标脚本判定，`_adapter.py`/`_case_gate.py` 标记为共享库，不再伪装成 CLI。`coverage_gate` 的“文件存在”不等于“能跑”，汇报时两个数分开说。方法、命令与 6 个剩余资产路径见 `references/callability-and-asset-paths-20261021.md`。
- 验收：`arsenal_build.py` 输出 total=2173/enabled=374/disabled=1799/legacy=1856；1,856 张 legacy 全有 catalog+body_path，0 缺失；`selftest.py` 30 条实战问句 Top5 **30/30**；实弹加载 `druid-console-unauth`、`hunt-subdomain`、`adcs-certipy-attack` 均出全文。
- **反模式**：为了“都能用”把 1,799 张全部解除禁用 → 索引回到 183KB，模型在 2,000+ 行里更选不中；禁用+全库检索才是正解。

### ★库重建硬坑（2026-10-21 实测）

- **根级卡漏索引**：`arsenal_build.py` 旧 glob 是 `*/*/SKILL.md`，漏掉 `skills/<card>/SKILL.md` 根级卡。改为递归 `**/SKILL.md`，并跳过 `references` 与 `.curator_backups`；分类取 `rel.split(os.sep)[0]`（根级记 `root`）。本次补回 `api-contract-mining`，total 2,172→2,173、enabled 373→374，`skill_find` 可命中。
- **删 DB 必删 WAL/SHM**：只 `os.remove(DB)` 会留下旧 `arsenal.db-wal`/`-shm`，下一次 `executescript` 报 `sqlite3.OperationalError: disk I/O error`。删三件（`DB`、`DB-shm`、`DB-wal`）再 build，build 后跑 `selftest.py` 验证 `route-hit 30/30`，不要只看 JSON。
- **覆盖率会被文档自身改写**：任何卡里出现 `tools/ops/<name>.py` 都会被 `coverage_gate.py` 计入唯一名，连 `coverage_gate.py`、`absorption_audit.py` 自己也算。新增工具或文档引用后必须重跑 gate，旧快照不能当当前结论。

操作入口见 `arsenal-router`（用户自有卡）；完整算法、数据模型、归档路径坑与验收矩阵见 `references/full-library-retrieval-layer.md`。本节只记可调用性验收口径与坑。

**长会话为什么会「不调用技能卡」**（源码核对，2026-10-21）：

1. 系统提示只放 `name + description` 一行；正文必须 `skill_view` 才进上下文——**从来没有自动加载正文**。
2. 压缩器把已读的 `skill_view` 结果替换成 `[SKILL_PRUNED: content lost in compression; reload with skill_view(name='...')]`，压缩后另附一条“reload these”提示（`agent/conversation_compression.py`）。旧卡正文被剪掉，不重读=没调用。**看到标记必须当场重载，别凭记忆干活。**
3. 窗口 <512K 的模型，`compression.threshold` 有 **0.75 地板（raise-only）**；config 里写 0.5 不代表 0.5 生效。200K 窗口 = 150K token 才压；system 已占约 6 万 token，留给对话约 9 万。一次 140KB 重卡约 4 万 token，两发就压。
4. 2,000+ 行索引本身稀释路由：全在 ≠ 选得中。长对话里前面的证据/工具输出会把注意力从索引拉走，表现为漏选/选错。

**缓解（按收益）**：① 减条目是唯一能压索引的手段（`hermes skills config` 或 `skills.disabled`）；先按 `skills_breakdown` 的 `index_line_total_bytes` 算家族账再决定砍谁。② 拆 >15K 字符重卡（中文约 45KB 字节；旧口径 >60KB 字节）：SKILL.md 留路由+判据，细节进 `references/`。③ 长战役每目标/阶段 `/new`，开头 20 行 case brief（目标/已拿/下一步/要用的卡），状态落文件。④ 开工 `hermes --skills a,b` 预载；每阶段开头重读 1–3 张关键卡。⑤ `[SKILL_PRUNED]` 当硬触发。

- 索引由 frontmatter 的 `name`+`description` 生成，**拆 references 不会缩小索引**；要缩只能减条目，或把分类降成 names-only（Hermes 内部 `compact_categories` 机制，目前仅 coding posture 用）。
- 930 张英文卡收进 `security-encyclopedia/references/` 后，索引只占 **1 条**——这是正确的 router 化样板。
- 名字全在索引时，`skill_view(name)` 是精确读文件，**卡数量本身不会导致“调不到”**；但会导致“选不中”+ 常驻预算被吃——两种问题分开治：调不到查撞名/改名，选不中才减条目。先量 `prompt-size` 再动刀。
- 索引快照缓存：`/root/.hermes/.skills_prompt_snapshot.json`；删掉再跑 `prompt-size` 可强制按当前库重建（本次由 2,158 条重建为 2,137 条）。

### 整库合并（减条目）执行顺序（2026-10-21 实测）

目标：2,000+ 张压到 300–400 张常驻；索引 183,732 chars → 约 31K chars / 38.6KB 字节（-83%），system 199,596 → 46,919 chars（-76.5%）。

1. **量账**：`hermes prompt-size --json` 存 `skills_breakdown[]`；按 `index_line_total_bytes` 算家族成本。再看 `~/.hermes/skills/.usage.json` 的 `use_count` / `last_used_at` / `pinned`。
2. **定 keep 集**：`use_count>=2` 或 14 天内用过，外加域母卡/essential；其余进归档。按“同一攻击面/同一决策路径”合，不按名字相似度合。
3. **建目录卡**：优先复用现有母卡（`whitelabel-gambling-pentest`、`php-framework-pentest`、`reverse-engineering` 等），没有才新建 `security-archive-index` / `general-archive`。
4. **搬正文**：每张被合卡的原 `SKILL.md` 复制成 `<目录卡>/references/legacy/<name>.md`；生成 `<目录卡>/references/index.md`（一行：`name — description — legacy 路径 — 原目录`）。**原目录不删**，脚本/字典/模板仍在原路径。
5. **改索引**：目录卡 SKILL.md 的 H1 后插 `<!-- MERGED-INDEX:START -->` 块，写清“先按本卡判据，不够再展开 index.md”；别把上千条正文堆进 SKILL.md。
6. **禁用**：`from hermes_cli.config import load_config, save_config`，写 `skills.disabled`；**禁止手改 config.yaml**。先 `cp config.yaml /root/backups/config.premerge.<ts>.yaml` + 落 `skill_merge_manifest.json`（keep/merged/catalogs）。
7. **补链**：扫所有 enabled 卡的 `](../<name>/SKILL.md)`；目标是 disabled 就回开（核心子卡），否则路由卡跳空。迭代到核心闭包；CTF/密码学链会级联，追 2–3 层就停，剩余走目录 index。
8. **验收**：`prompt-size` 索引/系统提示下降；`skill_view(旧名)` 返回 disabled；`skill_view(目录卡, 'references/legacy/<name>.md')` 能读全；index 条目数 = legacy 文件数；配置 `yaml.safe_load` 通过。
9. **回滚**：清空 `skills.disabled` + 恢复 config 备份；目录卡的 MERGED 块是增量，留着无害。

**坑**：
- disabled 后 `skill_view` **完全拒载**（不是只隐藏），所以正文必须先复制进目录卡。
- `skill_view(file_path=...)` 必须带 `.md`，否则 not found。
- 目录卡 description 可能是 `>-` 多行 YAML，别用 `[:-1]` 硬拼；只改单行 description。
- 非安全类卡先按路径分类搬去 `general-archive`，别混进 `web-sec`/`injection-checking`。
- `hermes skills list` 的 enabled 计数与 `prompt-size` 会差 1–2（pinned/essential/平台过滤），别追平。

