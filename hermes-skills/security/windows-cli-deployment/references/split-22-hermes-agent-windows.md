## Hermes Agent 安装（Windows + 中国网络）

2026-08 给新 Windows 机器装 Hermes（`irm https://hermes-agent.nousresearch.com/install.ps1 | iex`）按顺序踩过的三个坑：

### 1. 智能应用控制(SAC/WDAC)拦安装器下载的便携 python.exe

报错：`程序"python.exe"无法运行: An Application Control policy has blocked this file`。Hermes bootstrap 会下载便携 Python 到 `%LOCALAPPDATA%\hermes\bootstrap-cache\` 用于解析脚本/建 venv，被 SAC 或 WDAC 拒。全新 Win11 默认开着 SAC。

诊断（管理员 PowerShell）：
```powershell
# SAC 状态: 0=关 1=强制 2=评估
(Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -Name VerifiedAndReputablePolicyState -ErrorAction SilentlyContinue).VerifiedAndReputablePolicyState
CiTool.exe -lp   # 看 VerifiedAndReputableDesktop 策略是否 当前强制执行: true
```
修复：设置 → 隐私和安全性 → Windows 安全中心 → 应用和浏览器控制 → 智能应用控制 → 关闭（即时生效，无需重启）；或注册表 `Set-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -Name VerifiedAndReputablePolicyState -Value 0` + 重启。⚠️ SAC **关闭不可逆**（除非重置系统）、**无白名单功能**（WDAC 才能加白名单放行路径）。

### 2. 死系统代理 → "无法连接到远程服务器" / uv 报 os error 10061

症状：`irm` 连不上官网；uv pip install 阶段报 `Caused by: 由于目标计算机积极拒绝，无法连接。(os error 10061)`。原因：**uv/reqwest 会读 Windows 系统代理**——系统代理指向 `127.0.0.1:10808` 但 v2rayN/Clash 没开 → 全被拒。而 `git clone github.com` 能通（git 不走系统代理），浏览器也正常（插件代理/直连）——容易误判。

修复（管理员 PowerShell，一次粘贴整段跑；安装器会继承当前会话的环境变量）：
```powershell
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyEnable -Value 0
Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY -ErrorAction SilentlyContinue
$env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
$env:UV_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
$env:NPM_CONFIG_REGISTRY = "https://registry.npmmirror.com"
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
irm https://hermes-agent.nousresearch.com/install.ps1 | iex
```
先确认代理死活：`netstat -ano | findstr 10808` 有 LISTENING = 代理活着（直接重跑安装即可）；空 = 走镜像方案。后续 stages 的坑：node-deps 走 npm registry、desktop 构建要下 Electron 二进制（国内必须 `ELECTRON_MIRROR`）。

### 3. 断点续装

安装器支持缓存续跑：仓库 clone 到 `%LOCALAPPDATA%\hermes\hermes-agent`、uv/Python 校验通过后，重跑同一命令会跳过已完成 stages。若报缓存冲突，删 `%LOCALAPPDATA%\hermes\bootstrap-cache` 再装。日志在 `%LOCALAPPDATA%\hermes\logs\bootstrap-installer.log`（`Get-Content ... -Tail 80` 查 uv 报错原因）。

### 4. 安装器交互提示与可选组件坑

- **`Restore local changes now? [Y/n]`**：默认是 **Y（恢复）**，必须显式打 `n` 再回车。选 n——这是失败安装留下的半成品 stash，恢复会把脏文件弄回代码库。若输入没反应：① 鼠标点一下安装器窗口激活焦点 ② 按 Shift 切英文输入法（任务栏显示"英"）再打 `n`（中文输入法下字母会被吞成拼音）。
- **`npm install failed`（browser tools 阶段）**：不致命，配置向导走完后手动补：`cd "$env:LOCALAPPDATA\hermes\hermes-agent"; npm install --workspaces=false`。
- **cua-driver 下载失败（`连接被意外关闭` = GFW 重置 GitHub releases，重试 3 次全挂）**：cua-driver 只是 Computer Use（桌面控制）可选工具，**跳过不影响 Hermes 核心**（聊天/浏览器/终端/写代码）。可稍后在有代理的机器预下载 zip（`https://github.com/trycua/cua/releases/download/cua-driver-rs-<ver>/cua-driver-rs-<ver>-windows-x86_64.zip`）传过去手动装。

### 5. 配置向导（中国大陆选择）

- 总入口选 **2 (Full setup)** — 1 (Nous Portal OAuth) 走外网会卡死
- Inference Provider 选 **18 (DeepSeek)** — 国内直连最稳；key 在 platform.deepseek.com 拿
- Browser provider 选 **1 (Local Browser)**（默认，免费 headless Chromium，无需 key）
- Search provider 选 **11 (Skip)** — 其余要么注册 key、要么外网、要么自托管，先跳过以后配
- 向导问 API key 时：本机可用 ToDesk 共享剪贴板 `Set-Clipboard` 后远程 **Ctrl+V** 粘贴（免手打）；同步失败就本机记事本 Ctrl+C 一次强制刷新

### 6. 验证与启动桌面版

```powershell
hermes doctor
hermes chat -q "你好"     # 确认模型能回话
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
$env:NPM_CONFIG_REGISTRY = "https://registry.npmmirror.com"
hermes desktop            # 桌面版 = CLI 安装包自带，无需单独下载
```

- 桌面版首次启动：装 Node 依赖 → 从 npmmirror 下 Electron（~100MB）→ 构建 → 弹窗（2-5 分钟）
- **npm EBADENGINE**（系统 npm 版本在禁用区间，如 node v24.18.0 + npm 11.16.0 vs 要求 `<11.10.0 || >=11.17.0`）：Hermes 自动 `Provisioning a Hermes-managed Node.js runtime` 并升级受管 npm，**无需干预**，等它自愈
- `hermes doctor` 提示 "Run hermes setup to configure missing API keys" 属正常（工具集未配全），不影响核心使用

### 7. cua-driver 手动补装（GitHub 被墙）

zip 含 6 文件，只需 3 个 exe：
1. 有代理机器预下载 `https://github.com/trycua/cua/releases/download/cua-driver-rs-<ver>/cua-driver-rs-<ver>-windows-x86_64.zip`，传到目标机解压
2. 复制 `cua-driver.exe`、`cua-driver-uia.exe`、`cua-cursor-theme.exe` 到 `C:\Users\<user>\AppData\Local\Programs\Cua\cua-driver\bin\`
3. bin 加入用户 PATH：`[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path','User') + ';<bin>', 'User')`
4. 验证：`hermes computer-use doctor`
（`hermes computer-use install` 官方脚本源在 raw.githubusercontent.com，国内同样失败）

### 8. 桌面版启动：别直接双击 Hermes.exe（引导重装"自杀"坑）

`apps\desktop\release\win-unpacked\Hermes.exe` 是**纯前端壳**。直接双击 → 弹 "Set up Hermes Desktop" 引导；若选 "Install Hermes locally" → 它会**重装后端**，在 venv 阶段执行 `Stopping any running hermes processes before recreating venv...` **把自己杀了 → 闪退**，且**把已建好的 venv 弄坏**（venv\Scripts 只剩 python.exe，hermes.exe 消失 = `hermes` 命令从此找不到）。症状：日志停在 `-> Stopping any running hermes processes before recreating venv...` 后无下文 + `Test-Path venv\Scripts\hermes.exe` 为 False（python.exe 可能还在）。

修复 = 重跑官方安装器重建 venv（见第 2 节镜像命令；这次没有引导进程干扰不会自杀）。正确启动方式：
```powershell
hermes desktop    # 先起后端再拉壳（CLI 安装包自带桌面版）
```

桌面快捷方式必须指向 CLI 而非 Hermes.exe：
```powershell
$hermes = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\hermes.exe"
$desktop = [Environment]::GetFolderPath('Desktop')   # 勿用 $env:USERPROFILE\Desktop（可能被 OneDrive 重定向，建了桌面看不到）
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$desktop\Hermes.lnk")
$lnk.TargetPath = $hermes; $lnk.Arguments = "desktop"
$lnk.WorkingDirectory = "$env:LOCALAPPDATA\hermes\hermes-agent"   # 必须项目根目录！设成 venv 会闪退
$lnk.IconLocation = "$hermes,0"
$lnk.Save()
```

快捷方式启动的额外坑（2026-08 实测）：
- **WorkingDirectory 设错 = 黑窗口一闪即退**：`Split-Path (Split-Path $hermes)` 落在 `venv` 而非项目根，hermes desktop 找不到打包应用直接退出。必须是 `%LOCALAPPDATA%\hermes\hermes-agent` 根目录
- **venv 重建后旧快捷方式报"目标已更改或移动"** → 删掉重建（文件被删过重建，Windows 快捷方式缓存失效）
- **单实例锁**：已有桌面版实例在跑时再次启动秒退（黑窗口一闪）→ 先清干净：`Get-Process | ? { $_.ProcessName -match "hermes" } | Stop-Process -Force` 再开
- **从 cmd/PowerShell 启动的 Hermes 依附该终端**：关终端 = Hermes 跟着退（控制台进程树）。快捷方式是独立控制台不受影响，但那个黑控制台窗口（后端进程）要最小化别关
- **vbs 静默启动器不可靠**：`wscript.exe + .vbs` 方案在国内机器常失效（.vbs 文件关联被安全软件改成记事本，双击变成打开文件）——别走这条路

### 9. PATH：安装器只对安装会话临时生效

新开窗口 `hermes` 报 `CommandNotFoundException` 是正常的——安装器加 PATH 只对当时会话有效。用完整路径：`$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\hermes.exe`（venv 固定在该位置），或持久化用户 PATH（`[Environment]::SetEnvironmentVariable('Path', ...+';'+$scripts, 'User')`，重开窗口生效）。判断 venv 完好：`Test-Path ...\venv\Scripts\python.exe`（注意 python.exe 在 ≠ hermes.exe 在——hermes.exe 是 pip install 后的 console script）。

### 10. 重跑安装器后：会再弹配置向导 → Ctrl+C

`.env` / `config.yaml` 在 venv 外（`%LOCALAPPDATA%\hermes\`），重建 venv **不清配置**（DeepSeek key 等保留）。所以安装器跑完弹出的 Setup Wizard **直接 Ctrl+C 跳过**，别重配覆盖。验证配置还在：`& "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\hermes.exe" chat -q "测试"`。另：配置向导出现 = install 阶段（含 desktop 构建）全部成功。

### 11. GitHub 间歇性被墙（git fetch "Recv failure: Connection was reset"）

GFW 对 github.com 干扰是**概率性**的：同一台机器前一分钟 fetch 成功、后一分钟被重置。最治本 = 修好代理（见下）；否则重试循环直到通，通了立刻重跑安装器：
```powershell
cd "$env:LOCALAPPDATA\hermes\hermes-agent"; $i=0; do { $i++; git fetch origin 2>&1 | Out-Null; if ($LASTEXITCODE -eq 0) { "FETCH_OK"; break }; Start-Sleep 2 } while ($i -lt 10)
```
**v2rayN 的 xray.exe 报"应用程序控制策略已阻止此文件" = SAC 没关干净**：注册表方式改 `VerifiedAndReputablePolicyState=0` 必须**重启电脑**才卸载策略（设置界面关闭则即时生效）；重启后完全退出重开 v2rayN 再开系统代理（F10）。SAC 还拦着时，装了 v2rayN 也等于没有代理——这是"中转连不上/安装器网络失败"的隐藏前置原因。

远程协助他人机器（ToDesk 窗口驱动 + 何时移交命令）见 `references/todesk-remote-driving.md` + `scripts/todesk_ctl.ps1`。

