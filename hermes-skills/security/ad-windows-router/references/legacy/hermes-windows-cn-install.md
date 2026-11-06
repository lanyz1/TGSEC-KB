<!-- archived from /root/.hermes/skills/security/hermes-windows-cn-install/SKILL.md on 2026-10-21 -->

---
name: hermes-windows-cn-install
description: >-
  测绘引擎·Use when installing Hermes on Windows behind GFW.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/hermes-windows-cn-install`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hermes-windows-cn-install/…')`，不要相对 `references/legacy/` 解析。

# hermes-windows-cn-install（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/hermes-windows-cn-install/`

溯源（仅标记）：`hermes/autonomous-ai-agents`

---

# Hermes 中国大陆 Windows 安装排障

来源：2026-08 实机踩坑（朋友电脑，Win11，SAC 强制模式 + 死系统代理 127.0.0.1:10808）。

## 症状 1：`irm install.ps1 | iex` 报"无法连接到远程服务器"

**原因**：系统代理指向的本地端口（如 127.0.0.1:10808）背后没有活的代理软件 = 死代理。浏览器能上网（直连或插件代理）但 PowerShell/原生程序全挂。

**确认**：`netstat -ano | findstr 10808` 无 LISTENING 行 = 代理死。

## 症状 2：dependencies 阶段 `os error 10061`（目标计算机积极拒绝，无法连接）

**原因**：uv 走系统代理（reqwest 默认读 WinINET 代理）打到死端口。

**修复**（管理员 PowerShell 一次粘贴，安装器继承这些环境变量）：
```powershell
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyEnable -Value 0
Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY -ErrorAction SilentlyContinue
$env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
$env:UV_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
$env:NPM_CONFIG_REGISTRY = "https://registry.npmmirror.com"
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
irm https://hermes-agent.nousresearch.com/install.ps1 | iex
```
github.com 直连**不稳定**（2026-08-17 实测：连上但传输被掐断，`git ls-remote` 报 `fatal: expected flush after ref listing`）；PyPI/npm/Electron 走国内镜像。若提示关系统代理影响其他软件：装完可 `ProxyEnable -Value 1` 恢复（代理软件真活着时）。

## 症状 5：`[X] Installation failed: Failed to download repository (tried git clone SSH, HTTPS, and ZIP)` + ZIP 报"无法连接到远程服务器"

**原因**：github.com 直连被墙干扰，git clone 传输被掐断、codeload ZIP 下载也连不上（2026-08-17 实机复现）。

**确认**：`git ls-remote https://github.com/NousResearch/hermes-agent HEAD` 报 `expected flush after ref listing`（=连上但被断）。⚠️ 预检勿用 curl -w 判活：`-m` 超时退出码非零，会在 `-w` 已输出状态码后追加 FAIL（"200FAIL" 假象），`git ls-remote` 才是权威判据。实测镜像可用性：**ghfast.top ✅**；ghproxy.net / gh-proxy.com ❌（同样被断）；gitclone.com ❌（502）；mirror.ghproxy.com / github.moeyy.xyz ❌（000）。

**修复**（管理员 PowerShell，先设置 git 全局改写再重跑安装器）：
```powershell
git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"
irm https://hermes-agent.nousresearch.com/install.ps1 | iex
```
git clone 走镜像成功后不需要 ZIP 回退。此改写是全局的，装完可 `git config --global --unset-all url.https://ghfast.top/https://github.com/.insteadOf` 撤销（如不需要）。

## 症状 6：`Setup wizard` 向导（Full setup）逐屏答案

- 首页选 **2 (Full setup)**（1=Nous Portal OAuth 外网不稳，大陆必挂）
- 供应商列表 Choice [1-39]：**按名字找 DeepSeek**，勿按编号盲选（实测第 2 项是 Fireworks AI，选错会先进 Fireworks key 询问）
- 逐个供应商 API key 询问：**没有 key 的直接回车跳过**，直到 `DEEPSEEK_API_KEY` 粘贴 sk- 开头的 key
- Terminal backend：直接回车（默认 Keep current local）
- Select platforms：**全部不选，直接回车**
- `Start the gateway now after install? [Y/n]`：**输 `n`**（网关只给消息平台用，桌面版不需要）

## 症状 3：`程序"python.exe"无法运行: An Application Control policy has blocked this file`

**原因**：Smart App Control（智能应用控制）强制模式拦了 bootstrap 下载的便携 python.exe（无微软信誉签名）。

**确认**：
```powershell
(Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -Name VerifiedAndReputablePolicyState -ErrorAction SilentlyContinue).VerifiedAndReputablePolicyState
```
返回 1=强制 / 2=评估。`CiTool.exe -lp` 里 `VerifiedAndReputableDesktop` 策略"当前强制执行: true"即 SAC 激活；其余系统策略（Cross Certificates / Driver / Endpoint Security）不用动。

**关闭**：设置 → Windows 安全中心 → 应用和浏览器控制 → 智能应用控制 → 关（**不可逆**，关后不可重开除非重置系统；个人机一般无影响，先征得机主同意）。或注册表 `VerifiedAndReputablePolicyState=0` 后重启。

## 症状 4：重装/更新提示 `Local changes were stashed... Restore local changes now? [Y/n]`

**必须输入 `n` 再回车**（默认是 Y=恢复）。这些"本地改动"是上次失败安装留下的半成品残留，恢复会污染代码库导致再次失败。

## 其他要点

- 安装器预检顺序：uv → Python 3.11（系统已有则直接用）→ git → node → ripgrep/ffmpeg → clone 仓库 → venv → deps。
- 卡 dependencies 前先看日志：`Get-Content "$env:LOCALAPPDATA\hermes\logs\bootstrap-installer.log" -Tail 80`。
- 装完配置向导：大陆机器选 DeepSeek（国内直连）优于 Nous Portal OAuth（外网），逐屏答案见症状6。
- 装完 `hermes doctor`：核心项全绿即完成。**可忽略的 ⚠**：telegram-bot/discord.py（optional 未装）、各 OAuth 未登录（Nous Portal/Codex/xAI）、`state.db ... no such table: sessions`（新库首跑自动建，非错误）、缺 EXA/TAVILY/web 等 API key（要用对应工具再配）、Playwright Chromium（optional）、结尾 "Found 1 issue(s)" 泛提示。
- 桌面版不用单独下载：CLI 安装包自带，装完 `hermes desktop` 或开始菜单 Hermes 图标启动。
