# 可调用性与资产路径收口（2026-10-21）

## 结论

`coverage_gate` 只证明 `tools/ops/<name>.py` 存在，不证明脚本能跑。补充两层实测：

1. **callability**：`python3 tools/ops/callability_gate.py`
   - 154 个脚本：**152 ready / 2 library / 0 manual / 0 broken**。
   - `ready` = 编译通过且入口 `--help` rc 0/2；adapter 薄封装解析到目标脚本；`library` = 编译通过但没有 `__main__` 的共享 helper（`_adapter.py`、`_case_gate.py`）；`broken` = 语法/启动/超时。
   - 只跑 `--help`，不执行业务动作；无入口的 helper 不当作 CLI 调用。
   - `--strict` 只在 broken>0 时 exit 1。

2. **资产路径**：`python3 tools/ops/resolve_asset_paths.py [--apply]`
   - 扫描卡面 `docs/learning/*` 引用；只对“最后一级目录名 == 现有技能卡目录名”的路径建立 symlink。
   - 2026-10-21 执行 `--apply`：**284 个**路径创建 symlink，`absorption_audit` 的 `missing_store_paths` 从 **317 降到 6**（另生成 20 个索引/状态/模块页）。
   - 剩余 6 个都是无本地对应卡：yudao-tma-pentest、yudao-web-appapi-pentest、507mx-fastadmin-bola、tg-account-library-ops、tg-account-session-intake、telegram-gambling-tma-pentest，**不伪造**。

## 验收命令

```bash
cd /root/TGSEC-Qtzuu
python3 tools/ops/callability_gate.py --strict
python3 tools/ops/resolve_asset_paths.py --top 5
python3 tools/ops/absorption_audit.py --top 10
python3 tools/ops/coverage_gate.py --active --strict --top 3
```

## 注意

- `tools/ops` 有 155 个 `.py`，`callability_gate` 自排除自己，因此报告是 **154 个 checked**；当前 **152 ready / 2 library / 0 broken**。不要把 155 写成已检查数，也不要把 152 写成 154。
- adapter 薄封装先解析 `_adapter.run("target.py")`；目标在外部 `.claude/.../tools` 或本地 `tools/ops` 存在即 `ready`，不要因为“没有 argparse”直接判 `manual`。
- 无 argparse 但有 `__main__` 的脚本仍可跑 `--help`；`selftest` 这类测试入口 exit 0 也算 ready。只有共享 helper（无 `__main__`）才是 `library`，`--strict` 只在 broken>0 时红。
- symlink 是兼容层，不替代原始资产；卡内 `scripts/`、`data/` 仍需按来源整目录导入。
- 新增 `tools/ops` 脚本后重跑 callability；新增卡后重跑 `resolve_asset_paths.py`（先 dry-run）。
- 106 个 ops 名缺口与 6 个缺源卡资产缺口分开记账，不要合并成“全绿”。
