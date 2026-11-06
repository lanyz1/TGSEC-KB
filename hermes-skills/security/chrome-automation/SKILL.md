---
name: chrome-automation
description: >-
 测绘引擎浏览器作业入口：本机有头 Chrome（CDP 9222）、Scrapling 抓页、
 会员 Cookie 导入、极验滑块。用户提到本机 Chrome、CDP、远程调试、
 有头看操作、agent-browser、Playwright、Scrapling、session_pipeline、
 浏览器自动化环境 时使用。CF/会员站先验 session；桌面 IDA 走 browser-automation。
 打站/假支付/Actuator 仍走专卡。
owned: true
pack: survey-skill
---

# 浏览器自动化（测绘引擎）

本卡接到**现有作业链**，不是再装一套 `~/.claude` 的 agent-browser。

## 何时用

- 要看得到窗口的本机 Chrome（远程调试 9222）
- 授权站要渲染 / 过 CF / 带着会员 Cookie 点页面
- 用户说「浏览器自动化环境」

## 分流（先看这张表）

| 场景 | 走 |
|------|-----|
| 授权站抓页 / JS 渲染 / CF | Skill **`scrapling`** · `tools/scrapling/bin/scrapling_fetch.py` |
| 已有 Cookie / 会员态导入 | `python3 tools/ops/session_pipeline.py --domain … --input cookies.json --case …` |
| 图形码 | Skill `captcha-ocr` |
| 极验 / 滑块 | Skill `geetest-captcha-bypass` · `captcha_auto.py` |
| 本机有头 Chrome + CDP | 本卡下面的启动命令 |
| Windows 桌面（IDA / x64dbg） | Skill `browser-automation` 的桌面段 |
| JS 断点 / Hook | Skill `js-reverse` |

禁止：把个人 Chrome 主号整份档案同步到作业出口再打站（漏个人 Cookie）。作业用独立 profile 或 `session_pipeline` 导入的授权会话。

## 本机有头 Chrome（CDP）

```bash
# 空作业 profile，调试口 9222（默认不拷个人主号）
bash .cursor/skills/chrome-automation/scripts/start-chrome-mac.sh
# 只有你明确要求时才： bash .../start-chrome-mac.sh --import-personal
```

启动后：

```bash
# 授权站渲染抓页（优先本库 Scrapling，不要改走 ~/.claude 安装脚本）
python3 tools/scrapling/bin/scrapling_fetch.py https://授权站 --mode browser --case <案卷>
# CF
python3 tools/scrapling/bin/scrapling_fetch.py https://授权站 --mode stealthy --solve-cf --case <案卷>
```

`agent-browser` 仅在你本机已经装好、且目标在 scope 时用；缺依赖走 Scrapling / Playwright，**不要**跑 `auto-install-mac.sh` 去装 Rust/pnpm。

## 会员态

```bash
python3 tools/ops/session_pipeline.py \
 --domain 授权域 --input cookies.json --case <案卷> \
 --require-session --require-cf
```

## 强制

1. 目标在 scope。
2. 抓页/过 CF 默认 Scrapling；本卡只补「有头 Chrome / CDP」。
3. 滑块不走 OCR。
4. 桌面逆向 GUI 不走本卡。

## 真源

- 手法：`docs/playbooks/打网站手法.md`


---

## 外部库增量（2026-10-11 分享包）

## ⚠️ CRITICAL: Automatic Installation & Dependency Check

**BEFORE using this skill, ALWAYS run the auto-installation check:**

This skill automatically checks and installs all required dependencies without user confirmation. The installation process verifies:
- agent-browser repository and binary
- Node.js and pnpm
- Playwright Chromium
- Rust toolchain (cargo)
- Native binary compilation

**Auto-installation workflow:**

```bash
# Mac: Run auto-install script
bash ~/.claude/skills/chrome-automation/scripts/auto-install-mac.sh

# Windows: Run auto-install script (PowerShell)
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\chrome-automation\scripts\auto-install-windows.ps1"
```

**The script will:**
1. Check if agent-browser binary exists and works
2. Install missing dependencies automatically (pnpm, Rust, etc.)
3. Clone repository if not present
4. Build native binary with proper Rust toolchain
5. Verify installation success

**Critical rules:**
- ❌ DO NOT fall back to using built-in browser tools (browser_use_desktop)
- ✅ MUST run auto-install script before any browser automation
- ✅ Only proceed with browser automation AFTER successful installation
- ✅ Script handles all dependency checks automatically

**Why agent-browser is required:**
- Provides real-time visual feedback in user's actual Chrome browser
- Allows user to see and interact with automation in progress
- Offers precise element selection and interaction capabilities
- Built-in browser tools are NOT a substitute for this skill's functionality

## Quick Start

### First-time setup (automatic)

**Run the auto-install script first:**

```bash
# Mac
bash ~/.claude/skills/chrome-automation/scripts/auto-install-mac.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\chrome-automation\scripts\auto-install-windows.ps1"
```

The script automatically handles:
- Repository cloning
- Dependency installation (pnpm, Playwright)
- Rust toolchain setup
- Native binary compilation

### Connect and control Chrome

**IMPORTANT: Use the start-chrome script to preserve login states across sessions**

```bash
# Mac: Start Chrome with persistent profile (RECOMMENDED)
# This preserves your login states, cookies, and settings
bash ~/.claude/skills/chrome-automation/scripts/start-chrome-mac.sh

# Windows: Start Chrome with persistent profile (PowerShell)
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\chrome-automation\scripts\start-chrome-windows.ps1"

# Use agent-browser with --cdp flag
cd /Users/jyxc-dz-0100272/Documents/agent-browser
AGENT_BROWSER_HOME=/Users/jyxc-dz-0100272/Documents/agent-browser \
./bin/agent-browser --cdp 9222 snapshot -i
```

**What the start-chrome script does:**
1. First run: Creates a dedicated automation profile at `~/Library/Application Support/Google/Chrome-Automation`
2. First run: Imports your existing Chrome configuration (login states, cookies, settings)
3. Subsequent runs: Uses the existing automation profile - all your logins are preserved
4. You only need to log in once - it will be remembered for future sessions

## Core Workflow

**CRITICAL: Always show browser state to user after each significant action using screenshots.**

1. **Connect**: Ensure Chrome running with remote debugging port 9222
2. **Navigate**: Open pages using `--cdp 9222` flag
3. **Snapshot**: Get interactive elements with `snapshot -i`
4. **Interact**: Use element refs (@e1, @e2, etc.)
5. **Screenshot**: Capture state and show to user
6. **Report**: Describe what's visible in browser

### Standard operation pattern

```bash
# Set path variables
export AB_HOME=/Users/jyxc-dz-0100272/Documents/agent-browser
cd $AB_HOME

# Navigate
AGENT_BROWSER_HOME=$AB_HOME ./bin/agent-browser --cdp 9222 open https://example.com
sleep 2

# Get interactive elements
AGENT_BROWSER_HOME=$AB_HOME ./bin/agent-browser --cdp 9222 snapshot -i

# Screenshot to show user
AGENT_BROWSER_HOME=$AB_HOME ./bin/agent-browser --cdp 9222 screenshot /tmp/state.png

# Interact
AGENT_BROWSER_HOME=$AB_HOME ./bin/agent-browser --cdp 9222 fill @e1 "text"
AGENT_BROWSER_HOME=$AB_HOME ./bin/agent-browser --cdp 9222 press Enter

# Capture result
sleep 2
AGENT_BROWSER_HOME=$AB_HOME ./bin/agent-browser --cdp 9222 screenshot /tmp/result.png
```


## 全文导航（已拆分）

主卡保留前 10 节；其余 8 节在 `references/full.md`：

- Installation & Setup
- Chrome Connection
- Usage Patterns
- Real-time Feedback Protocol
- Command Reference
- Troubleshooting
- Best Practices
- Profile Management

加载：`skill_view(name='chrome-automation', file_path='references/full.md')`
