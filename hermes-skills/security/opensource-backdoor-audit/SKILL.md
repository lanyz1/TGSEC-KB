---
name: opensource-backdoor-audit
description: >-
  测绘引擎·Audit downloaded OSS repos for backdoors before use.
owned: true
tier: ops
pack: survey-skill
---

# opensource-backdoor-audit（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/opensource-backdoor-audit/`

溯源（仅标记）：`hermes/security-research`

---

# Open-Source Backdoor Audit

Trigger: user downloads a repo/app and asks "有没有后门 / 先检查 / is this safe / check for backdoors" before running it. Goal: give a definitive ✅/⚠️/❌ verdict backed by evidence, fast.

## Output format
Markdown table（检查项 | 结果）+ 总体结论 + "things to know" 列出**合法但需知情**的行为（默认关闭的通知通道、可选的云 API 调用、赞助链接等）。不要虚报后门，也不要在没有遥测时假装有。

## Workflow (in order)

### 0. Identify
Read README / README.zh-CN.md → what it is + tech stack (Tauri? Electron? Rust workspace? React?). Map structure: src-tauri/, scripts/, .github/, Cargo workspace dirs.

### 1. Git provenance
```bash
git remote -v              # 只应有官方 origin
git branch -a
git log --oneline | head -30
git rev-list --count HEAD
```

### 2. Suspicious-pattern scan (exclude node_modules/target/.git/*.lock)
```bash
grep -rniE "base64\(|atob\(|btoa\(|fromCharCode|eval\(|shell_exec|Invoke-WebRequest|irm |iwr " --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.cjs" --include="*.json" .
```
⚠️ `exec(`/`\.get\(` 命中多为误报（serde_json `.get("...")`、`which::which`、json 字段访问）。用 context 窗口复核再定论。

### 3. Hardcoded URLs/domains
```bash
grep -rnoE "https?://[a-zA-Z0-9\.\-]+" ... | grep -vE "<GOODLIST>"
```
GOODLIST：github.com, w3.org, tauri.app, rust-lang, docs.rs, anthropic, npmjs, shadcn, vitejs, typescriptlang, apache.org, gnu.org, reactjs, crates.io, wezterm, linux.do, openai, googleapis, schema., json-schema, example.com, localhost, 127.0.0.1, raw.githubusercontent.com, registry.*, opencollective + 项目 README/官网自己的域名。
标志项：未知 IP 嵌 URL、非标端口、短链、punycode。

### 4. IP scan
```bash
grep -rnoE "([0-9]{1,3}\.){3}[0-9]{1,3}" ... | grep -vE "127\.0\.0\.1|0\.0\.0\.0|255\.255|192\.168|10\.[0-9]|172\.(1[6-9]|2[0-9]|3[01])|1\.1\.1\.1|8\.8\.8\.8|100\.(6[0-9]|7[0-9])\."
```
100.64.0.5 = Tailscale CGNAT（100.64.0.0/10）→ tailscale 集成属正常。

### 5. Build/install-time artifacts（后门高发点，逐一读全文）
- Tauri: `src-tauri/tauri.conf.json` → updater endpoints（应为官方 GitHub Release）、pubkey（`echo ... | base64 -d` 应得到 "minisign public key: ..." 格式）、beforeBuildCommand 脚本、CSP、assetProtocol scope（scope `**` 要留意）
- NSIS 安装钩子 `src-tauri/nsis/*.nsh`：正常只做杀旧进程/卸载清理；出现 curl/下载/持久化 = 红旗
- 构建脚本 `scripts/*.cjs`（build-hook/copy-hook）：应只有 cargo build + 复制文件
- `.github/workflows/*`：找 secret 外发或注入步骤
- `build.rs` 逐个看

### 6. Runtime network exposure
- daemon/web bind：`default_value = "127.0.0.1"` = 好；0.0.0.0 / 默认 LAN = 红旗
- Web 认证：本机/远程来源分类（loopback vs remote + x-forwarded-for/tailscale-user-login 头）、远程只读模式、token 鉴权
- CLI hook（注入 Claude/Codex 会话的 hook）：确认只 POST 到本地 daemon（127.0.0.1 + Bearer 本地 token），不对外发

### 7. Credential handling
- API key 只注入子进程环境变量（ANTHROPIC_API_KEY 等）= CLI 管理器的正常行为；外发到任何远程 = 后门
- 读用户配置（~/.claude、settings.json）对 CLI 管理器正常，关键看数据后续去向

### 8. Telemetry/analytics
```bash
grep -rniE "telemetry|analytics|sentry|mixpanel|posthog|segment|amplitude" --include="*.rs" --include="*.ts" --include="*.tsx" .
```
无 = 干净。可选的推送通道（Telegram/DingTalk/Lark/Slack/Webhook 通知插件）标注为功能而非后门（默认关闭需用户配置）。

### 9. Dependencies
- Cargo.toml / package.json：是否全主流库
- `grep -E '^name = ' Cargo.lock | grep -iE "telemetry|analytics|sentry|posthog|exfil|reverse|rat"` —— 大多命中良性 crate（fallible-iterator、proc-macro-hack、gl_generator），看上下文

### 10. Obfuscation / dynamic exec
```bash
grep -rnE '"[A-Za-z0-9+/=]{200,}"'        # 长 base64（排除 pubkey）
grep -rnE '\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x'   # hex 转义串
grep -rnE "curl .*\|.*sh|download.*exec"
```
下载类功能必须有 checksum 校验（SHA256 对比）。

## Pitfalls（误报陷阱）
- 测试代码里的 "payload.exe" / "malware" 字符串 = 常是验证拒绝逻辑的 fixture，读测试上下文再定论
- provider.example / proxy.example / git.corp.example = 占位示例，不是外发端点
- 项目自身二进制名（如 cc-panes-daemon.exe）出现在生命周期代码里 = 自引用，非恶意
- tauri.conf.json 里的长 base64 = minisign 公钥，属预期
- 语音输入调云 ASR（DashScope/小米 MiMo）只有用户自配 key 才触发 = 数据流说明，非后门
- 声明的赞助中转站链接只是推广，看代码里是否真的引用其域名

## Support files
- scripts/audit_scan.sh — 一键跑全部 grep 扫描（git 溯源/可疑模式/URL/IP/遥测/base64/hex/可疑 crate），带良好过滤清单，减少误报
