## 工具（2026-09 上游收割补充：SAST 族）

- C/C++：`Flawfinder`、`Cppcheck`、`Clang-Tidy`、`PVS-Studio`(商业)
- Java：`FindSecBugs`(SpotBugs 插件)；PHP：`Psalm`(污点模式)、`phpstan`
- 依赖/SCA：`RetireJS`(前端库 CVE)、`npm audit` / `pip-audit`
- Go：`staticcheck`、`govulncheck`、`gosec`；已有 `Semgrep` / `CodeQL`
- Python：`Bandit`；Rust：`Clippy`；JS/TS：`ESLint` + security 插件
- 纪律：先用 SCA 收缩依赖面 → 再对**入口函数**跑 SAST → 最后人工确认数据流
