---
name: third-party-repo-audit
description: >-
  测绘引擎·Audit a cloned/downloaded repo for backdoors before running.
owned: true
tier: ops
pack: survey-skill
---

# third-party-repo-audit（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/third-party-repo-audit/`

溯源（仅标记）：`hermes/security-research`

---

# Third-Party Repo Backdoor Audit

Run this BEFORE building/running any unfamiliar repo. It's grep-driven and fast — no build needed. Answer the user's question ("有没有后门?") with a verdict table, not a yes/no guess.

## Phase 0 — Quick triage

```bash
# git hygiene
git remote -v                          # only official origin? no extra remotes?
git log --oneline | head -30           # sane history? suspicious giant "initial" commit?
git rev-list --count HEAD              # hundreds of commits = active; 1-2 = check carefully
git branch -a                          # extra branches may hide payloads
```

## Phase 1 — Hardcoded network endpoints (exfil/C2 hotspots)

```bash
# URLs — then FILTER OUT: github, w3.org, docs.rs, crates.io, npmjs, official SDK/API
# domains (anthropic, openai, mozilla, reactjs, tauri.app...), example.com, localhost
grep -rnoE "https?://[a-zA-Z0-9\.\-]+" --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.toml" . | grep -v node_modules | grep -v "/target/" | grep -v "\.lock"

# raw IPs — FILTER OUT: 127.0.0.1, 0.0.0.0, private (10.x/192.168/172.16-31),
# 100.64.x.x (Tailscale CGNAT — legit in tailscale tools), 1.1.1.1/8.8.8.8
grep -rnoE "([0-9]{1,3}\.){3}[0-9]{1,3}" --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.toml" --include="*.json" .
```

Anything left after filtering = investigate. `api.telegram.org` = notification channel (check if default-on). Unknown VPS = red flag.

## Phase 2 — Obfuscated payloads

```bash
# long base64 strings (200+ chars) — but WHITELIST updater pubkeys (minisign)
grep -rnE '"[A-Za-z0-9+/=]{200,}"' --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.cjs" .
# hex-escaped strings
grep -rnE '\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x' --include="*.rs" --include="*.js" .
# eval/dynamic-exec
grep -rniE "base64\(|atob\(|fromCharCode|eval\(|Invoke-WebRequest|irm |iwr |curl .*\|"
```

## Phase 3 — Build-time hooks (supply-chain attack point)

- **Installer hooks** (`*.nsh`, `*.iss`, `installer-hooks*`): legit = kill processes, cleanup, registry. Red flag = download+execute, PowerShell fetching remote content, writing to startup dirs.
- **Build scripts** (`scripts/*.cjs|*.js|*.py` referenced in tauri.conf beforeBuildCommand / package.json): legit = cargo build + file copy only. Red flag = network fetches, env exfil.
- **`.cargo/config.toml`**: check target-dir and any build overrides.
- **`build.rs`** files: scan for network/process-spawn code.

## Phase 4 — Auto-update & data egress

```bash
# updater endpoint (tauri.conf.json plugins.updater.endpoints)
#   legit = official GitHub release URL; pubkey base64 -d should decode to "minisign public key"
echo "<pubkey>" | base64 -d

# telemetry / analytics / reporting
grep -rniE "telemetry|analytics|track\(|sentry|mixpanel|posthog|segment|report|upload" --include="*.rs" --include="*.ts" --include="*.tsx" .
# API key handling: reading env vars is fine; hardcoded keys + POST to external = backdoor
grep -rnE "API_KEY|api_key|apiKey|Authorization.*Bearer" --include="*.rs" .
```

## Phase 5 — Runtime hooks that touch your sessions

CLI-agent managers (like cc-panes) install SessionStart hooks into Claude/Codex sessions. Verify:
- Hook reports only to **localhost daemon** (127.0.0.1) with a token = legit (session restore/memory injection).
- Hook POSTs to WAN endpoints = backdoor.
- Check daemon/web server bind default: `127.0.0.1` good; `0.0.0.0` without auth = exposure risk.

## Phase 6 — Dependencies

```bash
# deps must all be mainstream; grep lockfile for telemetry/malware crate names
grep -E '^name = ' Cargo.lock | sort -u | grep -iE "telemetry|analytics|sentry|exfil|steal|hack|rat"
# npm: python -c "import json; print(list(json.load(open('package.json')).get('dependencies',{}).keys()))"
```

## Phase 7 — 运行期取证（最强证据，比静态 grep 高一级）

静态扫描只能证明「代码里没写」，运行期能证明「实际没做」。三件套，成本极低：

```bash
# 1) 账号/审计表直读（SQLite 类应用）：有没有影子账号、有没有别人的登录历史
python - <<'PY'   # 或 write_file 成脚本再跑，避免内联 python -c 触发审批
import sqlite3; c=sqlite3.connect('file:data/app.db?mode=ro',uri=True)
for t in c.execute("select name from sqlite_master where type='table'"):
    if any(k in t[0] for k in ('user','session','audit','login')):
        print(t[0], c.execute(f'select count(*) from "{t[0]}"').fetchone())
PY
# 2) 出站连接：运行中进程零外部连接 = 没有心跳/回连/远控
netstat -ano | grep <PID> | grep -E 'ESTABLISHED|SYN_SENT'
# 3) 不授权实测：受保护端点无 token 必须 401，不只是「代码里挂了中间件」
for p in /api/projects /api/rbac/users /api/config/tools; do
  echo "$p -> $(curl -s -o /dev/null -w '%{http_code}' -m 8 http://127.0.0.1:8080$p)"; done
```

再看路由注册：`grep -nE '^\tapi\.(GET|POST|PUT|DELETE)\(' router.go` —— 有直接挂在根 group（未过鉴权中间件）的路由就是后门面。

## Phase 8 — 上游差分（换皮/魔改包必做）

1. 全树 blob SHA 比对（`git/trees?recursive=1` + 本地 sha256）：得出「一致 / 改动 / 本地新增 / 上游独有」四个数。
2. **只对鉴权/入口/网络类文件做逐行 diff**（`internal/security/`、`handler/auth*`、`app.go`、`cmd/main.go`），别对全树 diff，噪音淹没信号。
3. **差分前先做改名归一化**（`shengren-hacker→cyberstrike-ai`、`ShengRen→Sinian`、中文品牌名），否则模块名/品牌词把真实改动冲成大数字。
4. 读结论：鉴权文件 0 差异 = 没动鉴权；新增 `SecurityHeadersMiddleware` / `LoginGuard` = 作者在**加固**不是开后门。

## Pitfalls（实测踩坑）

- **`search_files` 对含转义/复杂的正则会给假零命中**（`exec\.Command`、`Middleware|RequireAuth` 全 0，而 `grep -rn` 同机同时命中 37 行）。**任何「0 命中」结论必须用 `grep -rn` 交叉复核**，否则会把「有」写成「无」。用 ASCII 锚点（如 `grep '^==='`）过滤脚本输出：Windows Python 管道输出的中文按 GBK 编码，UTF-8 的 grep pattern 匹配不到。
- Windows 上让 **Windows 版 Python** 读脚本参数路径时不要传 MSYS 的 `/tmp/x`（它会被当成 `C:\tmp\x`），传真实 Windows 绝对路径。
- GitHub API 匿名配额 60/h：批量抓上游文件做 diff 会中途静默失败 → 先把 raw 内容**落盘缓存再离线 diff**，并把失败显式打印出来。
- **裸 IP 命中先判是否只在 `_test.go` 里**（多为作者靶场/示例数据），生产路径无引用就不是后门。
- 归档包内附带的**已编译产物**（jar/zip/exe）常是作者的「上游旧构建」，字符串仍是旧品牌 → 换皮时需字节级改名并校验（jar: `this_class` 必须等于条目名；zip: 重打包后扫条目名）。
- 扫凭据/外联要覆盖 **`.md`/`.yaml`/技能库文档**，不只是源码：作者常把自己的中转站 key 与用量截图写进攻防笔记里。
- 排除目录先定好（`data/ log/ vendor/ node_modules/ 作者资产目录/ 备份`），否则命中全是噪音；同时**排除项要在报告里写明**，别让用户以为扫了全树。
- **审计边界要如实声明**：方法是定向的（外联面/鉴权面/持久化面/凭据面 + 关键文件差分 + 运行期取证），不是逐行通读 N 万行；未完成的部分（如配额用尽没 diff 成的文件）单独列出来，不假装覆盖。

## Deliverable

Verdict + table: `检查项 | 结果 (✅/⚠️/❌) | 说明`. Always include a "值得知道但非后门" section (optional notify channels, sponsor links, telemetry-free claims) so the user has full context. State clearly: "未发现后门" vs "发现 X 需处理" — no hedging.

## Reference

See `references/cc-panes-audit.md` for a full worked example (Tauri multi-crate desktop app, clean result) and the wallpaper-config knowledge that followed.
