# 技能库清理与死引用处置（2026-10-21）

## 一句话结论

技能库里的“缺失 ops”绝大多数是**卡面引用**，不是磁盘文件。删除引用可以让 gate 变绿，但那是假绿并会破坏原卡；真正能删的是未被引用的实体副本。

## 当前口径（2026-10-21 清理后快照；以 gate 实时输出为准）

- 全库：**232 个唯一 `tools/ops` 名，126 个有文件，106 个缺失**；引用 **1,268/1,543 = 82.2%**。
- 启用面：**124 个唯一名，115 个有文件，9 个缺失**；引用 **231/245 = 94.3%**。
- `coverage_gate.py --active --strict` 与 `--strict` 均 **exit 1**；`callability_gate.py --strict` 为 **exit 0**。不要把这两个 gate 混成一个“全绿”。

## 死引用扫描（删之前先量）

对每个缺失名，在 `/root/.hermes/skills/**/*.md` 中找 `tools/ops/<name>`：

- 命中 **216 个 md 文件 / 614 行**；
- 其中启用卡 **11 个文件 / 35 行**；
- 也就是说，一次性删引用会砍掉大量卡内命令和说明，不是“清理几个空文件”。

**处置规则**：默认不删卡内引用。要做就先生成 `DEAD-REFS.md`（文件、行号、缺失名），把原卡备份到 `/root/.hermes/skill-backups/<date>-deadrefs/`，再经操作员明确点名后逐条处理；否则保持 `manual` 并让 gate 红着。

## 本次实际删除了什么

操作员说“没有用的你就删除掉啊”后，只删了**实体文件**：

- `/root/.hermes/quarantine/20261021-safe-substitutes/`：5 个安全替代版 + README；
- `/root/.hermes/quarantine/20261021-unauthorized-narrowed/`：8 个收窄入口 + `_ops_http.py` + README；
- 合计 **16 个文件、0 残留**，随后删除空目录；
- 同步把 `CLOSURE-AUDIT.md`、`tools/ops/README.md`、`campaign-router`、审计 references 里的“已隔离/隔离区路径”改成“已删除/无保留副本”；重跑 `arsenal_build.py`（2,173 / 374 / 1,799 / 1,856）和 `selftest.py`（30/30）。

**删除后 gate 仍然是红的**：因为 106 个缺失名还在卡里。删除实体副本不等于补齐引用。

## 资产路径与 playbook 收口

- `resolve_asset_paths.py --apply`：对 `docs/learning/*` 只做**同名牌 symlink**，不复制、不伪造；另用 `consolidate_assets.py` 生成索引/状态/模块页。当前 **284 个 symlink、0 断链、20 个生成页、6 个缺源卡**。
- `resolve_asset_paths.py` 要跳过 `。` 这类标点污染路径，否则会把中文句号当目录名（本轮修过）。
- `consolidate_playbooks.py` 从现役卡生成 `docs/playbooks/*.md`：dry-run `refs=87 missing=86`，`--apply` 写 **86** 个；`docs/playbooks` 共 **88 文件 / 876K / 0 空文件**，3 个占位符（`*.md`、`<组件>`、`CVE日报-YYYY-MM-DD.md`）不建文件。

## 复验命令

```bash
cd /root/TGSEC-Qtzuu
python3 tools/ops/coverage_gate.py --active --strict --top 3   # exit 1，9 个缺口
python3 tools/ops/coverage_gate.py --strict --top 3           # exit 1，106 个缺口
python3 tools/ops/callability_gate.py --strict               # exit 0，见 gate 自报
python3 tools/ops/resolve_asset_paths.py --top 6             # unresolved=6
python3 tools/ops/consolidate_playbooks.py                   # missing=0 说明已生成
python3 /root/.hermes/arsenal/arsenal_build.py
python3 /root/.hermes/arsenal/selftest.py                    # 30/30
```

## 文档同步坑

- `tools/ops` 增加/删除脚本后，`callability` 的 checked/ready 数会变；不要抄旧文档，直接跑 gate 取 `total=... ready=... library=...`。
- 删除隔离目录后，所有“路径仍在”的 current-state 段落都要改成“已删除”；历史复盘段落可保留当时的处置过程，但不能让读者以为目录还存在。
- 报告里必须同时写“删了什么”和“gate 为什么还红”，不能只报删除数。
