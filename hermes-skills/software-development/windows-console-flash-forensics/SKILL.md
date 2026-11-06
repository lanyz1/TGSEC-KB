---
name: windows-console-flash-forensics
description: Windows 黑窗口/cmd 一直弹窗时用。进程审计定位源头 + 隐藏外壳修复。
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [windows, forensics, process-audit, console-flash, cygwin, bash, cron]
    related_skills: [windows-binary-reversing, remote-daemon-ops, monitoring-pipeline-ops]
---

# Windows 控制台闪窗取证与修复

## When to Use
- 用户说"电脑一直弹 cmd 窗口 / 黑窗口一直闪 / 是不是你的进程"
- 后台长跑脚本（bash 循环、cron、采集器）在无人值守时闪窗
- 需要判断某批控制台进程是不是自己（agent）拉起的

## 核心机理（先记住这条）
Windows 上**控制台窗口的创建由父进程决定**：

| 父进程类型 | 子进程行为 |
|---|---|
| 有控制台（console 子系统，如 cmd.exe、python.exe） | 子进程**继承**该控制台 → 不闪 |
| **无控制台**（GUI 子系统：pythonw.exe、Hermes.exe、wscript.exe、Electron） | 每个 console 子进程**必须自己分配**一个新控制台 → **闪一个窗** |

### ★ 窗口类名：先确定这台机器的"默认终端"（不查就会漏检，得出假阴性）
Windows 11 的 console 窗口**不再一定是 `ConsoleWindowClass`**。若"默认终端应用程序"被设为
**Windows Terminal**，则任何新控制台都由 WT 承载，可见窗口的类名是
**`CASCADIA_HOSTING_WINDOW_CLASS`**（标题通常是 `C:\Windows\System32\cmd.exe`），
同时 conhost 还会带一个（通常不可见的）`PseudoConsoleWindow`。
→ 只按 `ConsoleWindowClass` 枚举会得到"0 个窗口"的**假阴性**，据此下"没弹窗"的结论是错的。
**枚举白名单必须三个全带**：`ConsoleWindowClass` / `CASCADIA_HOSTING_WINDOW_CLASS` / `cygwin-console-helper`。

校验方法（30 秒，一次就能看出类名）：故意弹一个**稳定**靶子，看新增窗口的类名是什么——
```python
subprocess.Popen(["cmd", "/c", "ping", "-n", "20", "127.0.0.1"], creationflags=subprocess.CREATE_NEW_CONSOLE)
```
> **靶子绝不能用 `timeout N`**：ConPTY/Windows Terminal 下它因 stdin 不是真控制台而**秒退**，
> 窗口来不及出现 → 得出"没有窗口"的错误结论（本机踩过，白做一轮）。用 `ping -n N` 保活。
> 判据看进程的 `MainWindowHandle`：为 0 说明该进程本身没有窗口（WT 场景正常，窗口挂在 WindowsTerminal.exe 上）。

MSYS/Git-Bash 特殊：原生程序（curl.exe / wc.exe / head.exe / git.exe 等）在父进程无控制台时，会调用
**`cygwin-console-helper.exe` 新建一个可见控制台**——这就是"闪窗"的直接元凶。
所以判据是：**`cygwin-console-helper.exe` 高频出现 = 可见窗口在闪**。
（`conhost.exe` 被创建 ≠ 窗口可见：`CREATE_NO_WINDOW`/`windowsHide` 也会创建 conhost，但无窗口。）

## 诊断步骤（按顺序，别跳）

### 1. 判断是不是 Hermes 的进程
```bash
tasklist | grep -iE "cmd\.exe|conhost|cygwin-console-helper|bash|python"
process(action='list')      # 看自己的后台进程
cronjob(action='list')      # 看定时任务
```
注意：`cmd.exe /d /s /c ""...chrome-native-host.bat"` 是 Chrome 扩展原生消息宿主，**常驻不弹窗**，别误判。

### 2. 打开进程创建审计拿权威证据（管理员必需）
`auditpol` 子类名中文系统会乱码，**必须用 GUID**：
```bash
# 开启（0CCE922B... = Process Creation）
auditpol /set /subcategory:"{0CCE922B-69AE-11D9-BED3-505054503030}" /success:enable

# ... 采样 60-120 秒 ...

# 读 4688 事件（PowerShell，解析 XML 取 NewProcessName / ParentProcessName）
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688; StartTime=(Get-Date).AddSeconds(-120)} -MaxEvents 4000

# ★结束后必须还原原状态（默认就是 No Auditing）
auditpol /set /subcategory:"{0CCE922B-69AE-11D9-BED3-505054503030}" /success:disable
```
读出来按 `子进程 <- 父进程` 分组计数，一次就能看出元凶（例：`cygwin-console-helper, bash.exe  238`）。

### 3. 定位具体脚本
```powershell
Get-CimInstance Win32_Process -Filter "Name='bash.exe'" |
  ForEach-Object { '{0} <- {1} :: {2}' -f $_.ProcessId, $_.ParentProcessId, $_.CommandLine }
```
常见真身：`bash xxx.sh`（循环里调 curl/wc）、`bash -lic "..."`（agent 的 terminal 会话）。

### 4. 确认"是否真有可见窗口"（避免自己吓自己）
枚举顶层窗口，只看 ConsoleWindowClass 且可见的：
```powershell
Add-Type 'public class W{ [DllImport("user32.dll")] public static extern bool EnumWindows(...); ... }'
# 关键 API: EnumWindows + GetClassName + IsWindowVisible + GetWindowThreadProcessId
# class 含 ConsoleWindowClass / CASCADIA / PseudoConsoleWindow
```
全系统只剩个位数 = 风暴已停。

### 5. 定时弹窗 → 先查计划任务（schtasks 中文乱码，别用它）
用户说"**定时**弹一个 cmd 窗口"时，源头几乎总在任务计划程序里。
```bash
# ★ schtasks /query 输出 GBK，grep 中文任务名必失败 —— 改用 PowerShell
powershell.exe -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-ScheduledTask | Where-Object {\$_.TaskPath -notlike '*Microsoft*'} | ForEach-Object { \$a=(\$_.Actions|ForEach-Object{\$_.Execute+' '+\$_.Arguments}) -join ' ;; '; '{0} | {1} | {2}' -f \$_.TaskName,\$_.State,\$a }"
```
**弹窗判据**：任务的 `<Command>` 是 `cmd`/`cmd.exe`（console 子系统）且 Principal 为 `InteractiveToken`
→ 每次触发都新建可见控制台 = 闪窗。反例：入口用 **`pythonw.exe`** 或 **`wscript.exe`** 的任务不闪。
两侧交叉验证：**日志文件最后写入时间 == 任务 `LastRunTime`** 才能证明它确实在跑（本机 `task.log` 与
`LastRun` 对到同一秒，直接锁定元凶）。`task*.log` + `ledger.jsonl` 这类自带流水是更硬的证据。
另注：任务计划程序 Operational 日志**默认未启用**（`Get-WinEvent -ListLog ...` 返回 `IsEnabled=False`、0 记录），
所以"谁启用了/禁用了这个任务"查不到历史，不要在这上面耗时。

## 修复

### A. 立即止血 —— 杀进程树（★必须先获用户同意）
```bash
for p in <pid1> <pid2>; do cmd /c "taskkill /F /T /PID $p"; done   # /T 连带子进程
```
同时 `cronjob(action='pause', job_id=...)` 暂停会不断拉起新进程的定时任务。
停止后**从 4688 再读一遍**验证速率下降（例：2797/120s → 364/100s 且无 cygwin-console-helper）。

### B. 防复发 —— 用隐藏外壳跑长跑 .sh（首选，零改动）
原理：让进程树最顶层拥有**一个隐藏控制台**，全后代继承 → 不再新建。
`_run_hidden.vbs`（实测有效）：
```vbs
Option Explicit
Dim fso, sh, scriptName, workDir, bashExe, base, cmdLine
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
scriptName = WScript.Arguments(0)
workDir = fso.GetParentFolderName(WScript.ScriptFullName)
bashExe = "D:\Git\bin\bash.exe"
base = fso.GetBaseName(scriptName)
sh.CurrentDirectory = workDir
' ★窗口样式 0 = 隐藏；末参数 False = 不等待
cmdLine = """" & bashExe & """ -lc ""bash " & scriptName & " > _hidden_" & base & ".log 2>&1"""
sh.Run cmdLine, 0, False
```
用法：`wscript _run_hidden.vbs lnum.sh`（日志落 `_hidden_lnum.log`）
> 不要用 `cmd /c` 再套一层去拼引号——直接 Run bash.exe，重定向写在 `-lc` 的引号内，最稳。

### C. 治本 —— 把 bash 循环改成 python 单进程
一个进程反复 requests/http.client（含代理、连接复用），比"每密码一个 curl"快得多，且**结构上不可能闪窗**。
爆破场景可直接用 `http.client.HTTPSConnection` + `threading` 线程池 + 断点续跑。

### E. 计划任务闪窗 → VBS 隐藏外壳（命令原样保留，只改窗口样式）
把任务的 `<Command>` 改成 `wscript.exe`、`<Arguments>` 改成 `//B //Nologo "<vbs路径>"`，VBS 内：
```vbs
sh.Run "cmd /c cd /d """ & root & """ && """ & py & """ """ & script & """ sync --apply >> """ & log & """ 2>&1", 0, False
```
> 保留 `cmd /c` 是为了保住 `>> log 2>&1` 重定向语义；`0` = SW_HIDE 隐藏窗口，`False` = 不等待。
> 实测有效：同机制 A/B 对照里 style=1 弹出 1 个窗口，style=0 为 0 个。
> **VBS 内不要出现任何非 ASCII 字面量**（含中文路径）：全部从 `WScript.ScriptFullName` 上溯反推
> （ops→tools→root），文件纯 ASCII → 编码永远不会坏。

**★ 改任务定义时不要在命令行里传中文路径**（bash→powershell 的编码链会毁掉它）。安全姿势：
```bash
powershell -NoProfile -Command "Export-ScheduledTask -TaskName '<名>' | Out-File -Encoding Unicode '<ascii路径>.xml'"
# 用 Python 改 XML 里的 <Command> / <Arguments> / <Enabled>，再以 encoding='utf-16' 写回
schtasks /Create /TN "<名>" /XML "<ascii路径>.xml" /F     # 导入前务必先备份原 XML，可一条命令回滚
```
> `/Create /XML ... /F` 会**整份覆盖**任务定义（Triggers / Principal 全部保留自 XML），是唯一能绕开中文编码的可靠改法。

**验证必须带正对照**，否则"0 命中"可能只是测量手段失效：
| 对照 | 机制 | 期望 |
|---|---|---|
| 正 | `sh.Run(cmd, 1, True)` | 捕获 ≥1 个可见窗口 |
| 反 | `sh.Run(cmd, 0, True)`（= 本方案） | 0 个 |
正有反无 → 才算证明。同时要求"功能真的跑了"（日志/流水增量），证明是**跑起来但没窗口**，而不是压根没启动。

### D. 断点续跑
循环脚本停掉会丢进度，续跑前先看进度日志（如 `grep -E "^prog " local_num.log | tail`），改 `seq` 起点。

## Pitfalls（踩过的坑）
1. **`Register-CimIndicationEvent -Query "SELECT * FROM Win32_ProcessStartTrace"` 可能返回 0 事件**（订阅静默失效）——别在这上面浪费时间，直接上 4688 审计。
2. `auditpol /get /subcategory:"Process Creation"` 在中文系统报 Usage 错，**一律用 GUID**。
3. 4688 的 `CommandLine` 字段默认为空，但 `NewProcessName` / `ParentProcessName` 足够定位；要命令行就用 WMI 轮询（120ms 间隔）抓活跃进程。
4. **`conhost.exe` 被创建不等于窗口可见**。真正可见的元凶看 `cygwin-console-helper.exe`。
5. 采样脚本反复跑容易被 Hermes 审批护栏拦（"timed out without user response"）——被拦后**不要原样重试**，换更简单的命令或直接汇报。
6. 审计策略是**系统级改动**，任务结束必须还原成 `No Auditing`。
7. 一个脚本树可能有多层（`bash ← bash ← bash`），杀最上层的 `/T` 即可；但**别杀 Hermes gateway 的 python.exe**（会掐断所有会话）。
8. 进程消失得很快：`Get-CimInstance` 快照查父进程常得到空（父已退出），此时以 4688 的 `ParentProcessName` 为准。
9. **窗口枚举的采样间隔决定了能否抓到短命窗口**：0.4~0.5s 一次对存活数秒的窗口足够；
   但若窗口只闪 <0.5s，单一采样会漏——此时靠 4688/进程快照交叉验证（"有进程创建但无窗口"= 隐藏成功）。
10. **`Get-Process | ? {$_.MainWindowTitle}` 是快速看"当前有哪些可见主窗口"的廉价办法**，
    可作为窗口枚举的交叉参考（含 Cursor/Chrome 等，用来确认枚举没整体失灵）。
11. 用 Python 从**无控制台的父进程**（pythonw / Hermes 自己的会话）起 console 子进程，
    即复现了闪窗机制——做正对照时正好用得上；反之从**有隐藏控制台**的父进程起子进程不会闪，
    所以"在我自己 terminal 里跑一下看闪不闪"得到的是假阴性。
12. 用 `pythonw.exe` 跑观测脚本，**不要 `print`**（stdout 为 None 会抛异常）：结果一律写文件，
    再用 read_file / cat 取回。

## 一句话总结
`cygwin-console-helper` 高频 = 可见闪窗；源头是无控制台的父进程拉起了狂调原生 exe 的 bash 循环；
止血靠 `taskkill /T` + 暂停 cron，防复发靠 **wscript 隐藏外壳** 或 **python 单进程改写**。
