# 吸收溯源审计：卡面 ≠ 运行层（2026-10-21）

## 结论

之前把 2,000+ 张技能卡“吸收”进库时，**只落了 `SKILL.md` 文本**，没有落 `scripts/`、`templates/`、`assets/`、数据目录。表现是：`skill_find` 能命中、`skill_view` 能读，但卡里的 `run: tools/ops/xxx.py` 是死路径。

这不是“文件丢了”，是**从未导入**。

## 实测证据

- `arsenal.db`：**2,173 张卡**（`enabled=374` / `disabled=1,799` / `legacy=1,856`）。
- `pack: survey-skill`：**194 张**，来自 **21 个来源**：
  - `trailofbits/skills` 78
  - `hermes/software-development` 30
  - `hermes/security-research` 17
  - `hermes/creative` 13
  - `anbeime/skill-local` 8
  - `anthropics/skills` 7
- **195 张卡**引用 `docs/learning/skill-store/skills/<name>/`（其中 193 张是 survey 卡）；该目录原先不存在，2026-10-21 已为 284 个精确同名牌建立 symlink 兼容层。
- **309 张卡**至少有一个缺失的 `docs/learning/*` 路径；历史合计 **317 个唯一路径**，284 个已建 symlink、20 个已生成索引/状态页，当前剩 **6 个**缺源卡。
- 194 张 survey 卡中：**49 张还有脚本**（合计 298 个），**145 张一个脚本都没有**；只有 110 张有 `references/`。
- 全盘扫描 **90 个 tar/zip 归档**（含 `.curator_backups`），117 个缺失 `tools/ops` 名命中 **0 个**。

## 合并器为什么只落文本

`/root/skill_merge.py` 的归档段（约 181–194 行；下面是**逻辑示意**，逐字以实际文件为准）：

```python
for name, key in assigned.items():
    ...
    with open(os.path.join(legacy_dir, safe + ".md"), "w") as f:
        f.write(f"<!-- archived from {path} on {STAMP} -->\n\n")
        f.write(text)          # 只有 SKILL.md 文本
    index_lines[key].append((name, desc, rel, path))
```

它**没有** `copytree`、没有复制 `scripts/` / `templates/` / `assets/` / 数据文件。原目录若本来就没附件，归档后也不会有。

## 审计入口

TGSEC 工具：

```bash
cd /root/TGSEC-Qtzuu
python3 tools/ops/absorption_audit.py --top 20
python3 tools/ops/absorption_audit.py --write /root/.hermes/arsenal/ABSORPTION-AUDIT.md
```

输出：卡总数、pack/source 分布、缺失 `docs/learning/*` 路径、缺失 `tools/ops` 名及其引用卡。

## 未来吸收的硬清单

每张卡必须核对并实际复制：

- `SKILL.md`
- `references/`
- `scripts/`
- `templates/`
- `assets/`
- `data/` / 字典 / 语料
- `tests/`（如果有）
- `agents/`（如果有）

记录：`source`（repo/URL/commit）、`sha256`、`license`、`asset_status`。只拿到文本的卡标 `asset_status: text-only`，不得把卡内命令当“已具备”。

## 两个重建硬坑（同次踩过）

### 1. 根级卡漏索引

旧 `arsenal_build.py` 只扫：

```python
glob.glob(os.path.join(ROOT, "*", "*", "SKILL.md"))
```

根级技能（如 `/root/.hermes/skills/api-contract-mining/SKILL.md`）不在两级 glob 内，实测 total 2,172 / enabled 373，比文件系统少 1 张。修法：

```python
for p in glob.glob(os.path.join(ROOT, "**", "SKILL.md"), recursive=True):
    rel = os.path.relpath(p, ROOT)
    parts = rel.split(os.sep)
    if "references" in parts or ".curator_backups" in parts:
        continue
    cat = parts[0] if len(parts) > 1 else "root"
```

修复后：`total=2173 enabled=374 disabled=1799 legacy=1856`；`skill_find "API contract mining"` 命中 `api-contract-mining`。

### 2. 删 DB 不删 WAL → disk I/O error

重建脚本先 `os.remove(DB)`，但残留 `arsenal.db-wal` / `arsenal.db-shm` 时，SQLite 会在 `executescript` 阶段报：

```
sqlite3.OperationalError: disk I/O error
```

正确做法：

```python
for suffix in ("-wal", "-shm"):
    try:
        os.remove(DB + suffix)
    except FileNotFoundError:
        pass
os.remove(DB)
```

重建后必须跑 `selftest.py`，确认 `route-hit 30/30`，不要只看 build 的 JSON。

## 覆盖率的连带效应

`coverage_gate.py` 扫描所有技能 `.md` 中的 `tools/ops/<name>.py` 字样。**只要某张卡提到新脚本名，唯一名/引用数就会变**；连 `coverage_gate.py`、`absorption_audit.py` 自己也会被算进去。

- 加工具/加文档引用后必须重跑：
  ```bash
  python3 tools/ops/coverage_gate.py --top 20
  ```
- 旧快照只能当历史，不准直接抄进当前结论。
- **计数会漂移**：以 `python3 tools/ops/coverage_gate.py --top 20` 的实时输出为准；文档里的“当前快照”一律标明采集时间。
- 2026-10-21 清理后的实测快照：全库 **232 唯一 / 126 实现 / 106 缺；1,268/1,543 = 82.2%**；启用卡 **124 唯一 / 115 实现 / 9 缺；231/245 = 94.3%**。这组数已包含清理后的文档改动，仍不是永久值。

## 106 个缺失 ops 的归因（2026-10-21 追问实测）

用户问“为什么缺、没有来源了吗”时，不要只答“没导入”。先做四层取证，结论要区分**卡源**和**脚本源**：

1. **全盘 exact-name**：`find /root -name '*.py'` 量级 41,852；再对 106 个名字逐个匹配，105 个命中 0。`domains/` 1,822 个 py、技能目录 665 个 py 也没有。
2. **git 全历史**：TGSEC 仓库 87 个 commit；`git log --all --name-only --pretty=format:` 对 106 个 basename 只命中 1 个：`orchestrator.py`，路径是 `domains/redteam-framework/aimy-tools/orchestrator.py`；`git ls-files tools/ops` 输出 **0**。
3. **卡目录附件**：引用缺失名的 107 张 `SKILL.md` 中，只有 **1 张**有 `scripts/` 目录（且无 `.py`），**0 张**卡目录里有任何 `.py`；216 个 md（含 legacy/拆分引用）共 614 行，175 个名字只出现 1 次。
4. **归档/来源字段**：90 个 tar/zip 归档 0 命中；`absorption_audit.py` 显示这些缺失名所在卡基本没有 `溯源` 字段，不是从有脚本的 pack 导入的。

**典型证据**：

- `security/ollama-unauth/SKILL.md` 只有一张卡，没有 `scripts/`；
- `security/fixed-flow-pentest-platform/SKILL.md` 自称 `flow_runner.py` “均已实测”，目录里只有 `SKILL.md`；
- `security/orchestration-layer/SKILL.md` 指向 `D:\测绘引擎\...`，工具层在另一台机器/平台；
- 唯一有历史文件的 `orchestrator.py` 是 90KB AIMY 框架应用，`import tools.auth_bypass / crawler / jwt_exploiter...` 依赖在本机不存在，搬进 `tools/ops` 也不能跑。

**结论**：105/106 不是“文件丢了”，而是**卡面点名了从未落地的工具**；1/106 只有不可运行的旧框架文件。9 个启用面缺失正是此前擅自写的实现（已删除），其余 97 个只在 disabled/legacy 卡。若原平台机器 `D:\测绘引擎` 仍可访问，才可能找回原版；本机无挂载/备份，否则只能按卡重写新实现，不能叫恢复。

## 缺口性质

- `css_query`（11 张卡 / 22 处引用）：缺 `docs/learning/cybersecurity-skills` 数据，不是脚本本身。
- `rce_forge`、`strike_probe`、`host_c2_verify`、`payload_forge`、`se_listen`、`sig_cleanup_scan`、`se_inject` 等 13 个擅自写的实现已按操作员要求删除（无隔离副本），原卡文本未改，按 `manual` 处理；不提供木马/C2/免杀/身份注入的可执行替换。
- `ato_reset_withdraw_probe`、`fund_edge_ops_probe`、`social_engineer_agent` 也已删除，按 `manual` 处理；需资金/TG 实号链时不提供收窄替代。
- 没有真实数据/授权时标 `manual`，不写空壳。
