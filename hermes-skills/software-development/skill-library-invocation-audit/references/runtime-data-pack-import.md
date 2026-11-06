# 运行层数据包补全实战（2026-10-21）

## 症状

`skill_find`/卡面能看到 `css_query.py`、外部 `tools/ops` 命令，但本机没有文件；卡又声称“全文在 `docs/learning/skill-store/skills/...`”。这不是脚本损坏，而是吸收时只搬了 `SKILL.md` 文本。

## 已跑通案例：CyberSecurity-Skills

- 上游：`https://github.com/hi-fullhouse/cybersecurity-skills`
- 许可：MIT；commit `67d35c0c`
- 结构：39 模块 / 195 技能；查询 CLI 是 `skill_query.py`，不是卡面写的 `css_query.py`
- 落位：`docs/learning/cybersecurity-skills/`（完整目录，删除 `.git`）
- 元数据：新增 `SOURCE.md`；上游无 `CATALOG.md` 时按 `index.json` 生成；本地专属 `00-测绘引擎业务-SurveyEngine/MODULE.md` 单独写
- 适配器：`tools/ops/css_query.py` 把卡面的 `list-modules/list-skills/search/get/doctor` 映射到上游命令，`os.execv` 转发
- 验证：`css_query.py doctor` → 声明 195 / 实际 195；`list-modules`、`search --keyword 无线`、`get --id 05-002` 都有输出
- 结果：22 处 `css_query` 死引用清零

## 两个审计脚本

```bash
python3 tools/ops/absorption_audit.py --top 20
python3 tools/ops/coverage_gate.py --top 20
python3 tools/ops/coverage_gate.py --strict   # 仍有死引用时 exit 1
```

- `absorption_audit`：缺失 `docs/learning/*` 路径、缺失 ops 名、来源分布。
- `coverage_gate`：唯一名已实现/仍缺、引用覆盖；启用卡与全库分开统计。
- 每补一个包/脚本，重跑两者并按输出改文档；不要保留旧百分比。
- 审计路径时对 `.../11-` 这类截断做目录前缀匹配，否则会把真实模块误报为缺失。

## 本轮补的通用入口（可复用套路）

- `email_sec_probe.py`：本地 `.eml`/lure HTML 解析，不发网络请求。
- `cicd_surface_probe.py`：本地仓库 CI 配置静态扫描（`pull_request_target`、`write-all`、未固定 action、`curl|bash`、docker socket）。
- `oauth_oidc_surface_probe.py`：OIDC discovery + redirect_uri，必须 `--scope`，fail-closed。
- `session_import.py`：Cookie 导出按域过滤，输出 `session.json` + Netscape `cookies.txt`；只输出计数，不打印值。
- `litellm_badhost.py`：Host 头绕过只读探测；`loot` 对 key/token 做 `***REDACTED***`。
- `nextcaptcha_solver.py` / `capmonster_solver.py`：真实 API 适配；key 从 `--api-key` 或环境变量读，缺 key `exit 2`，绝不返回假 token。

## 测试纪律

- 每个脚本至少跑：`--help`、正常输入、错误输入；网络探针用本地 mock（HTTP server + 临时端口），跑完 kill。
- 适配器必须 `py_compile`；`coverage_gate` 只认真实文件，空壳会被下一轮审计打回。
- 不能因为“已补 120 个”就说“229 个都可用”；`--strict` 仍 exit 1 时要如实报剩余数。
