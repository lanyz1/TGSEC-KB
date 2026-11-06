<!-- archived from /root/.hermes/skills/software-development/windows-scheduled-task-ops/SKILL.md on 2026-10-21 -->

---
name: windows-scheduled-task-ops
description: Use when 排查 Windows 计划任务(定时弹窗/某任务是什么/还在跑吗)。盘点→判读→证据→改入口。
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [windows, schtasks, scheduled-task, console-flash, ops, evidence]
    related_skills: [windows-console-flash-forensics, remote-daemon-ops, monitoring-pipeline-ops]
---

> 归档卡：原目录 `/root/.hermes/skills/software-development/windows-scheduled-task-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/software-development/windows-scheduled-task-ops/…')`，不要相对 `references/legacy/` 解析。

# Windows 计划任务运维与判读

## When to Use
- "定时会弹出来一个 cmd 窗口 / 黑窗口" —— 定位那是哪个任务
- "这个计划任务是什么 / 干嘛用的 / 还在跑吗" —— 解读既有任务（含 agent 自己注册的那些）
- 盘点本机所有非官方计划任务（自建、agent 注册的后台自动化）
- 注册新的定时自动化（要求零弹窗）、或改/停一个既有任务

深度闪窗取证（4688 审计、`cygwin-console-helper` 机理、隐藏外壳 VBS、python 单进程改写）见
`windows-console-flash-forensics`；本卡管**任务生命周期**：盘点 → 判读 → 证没证在跑 → 改入口 → 注册。
> 注：那卡里"入口是 `pythonw.exe` 就不弹窗"的旧判据已作废（实测 venv 的 `pythonw.exe` 是 CONSOLE 子系统），
> **一律以本卡 §2 的 PE `Subsystem` 判据为准**。

## 铁律（每条都是踩出来的）
1. **定时弹窗先查计划任务，不先翻进程**：闪窗进程活几秒就没了，而任务定义永远在。
2. **系统级改动先给方案表**：改/停/删/启任务（`/Change` `/Delete` `/End` `/Create`）属系统级改动——
   先给"现状证据 + 方案对照表 + 副作用"让用户点单，不擅自执行。
3. **说弹窗必须连带说功能代价**：禁用一个任务 = 它承诺的自动化静默断供（例：自动同步/收编不再发生）。
   只报"关掉了"不报"少了什么"= 不合格交付。
4. **证据只认三样**：`State` + `LastRunTime` + **任务自己的产物日志 mtime**。
   `NextRunTime`（Disabled 也有残留值）与 Prefetch 都不可信，别拿它们当证据。
   把一个**窗口**归因给某个任务时必须三路交叉（只看"时间接近"会被一秒之差骗到）：
   ① 命中时刻 == 触发点，且与 `LastRunTime` 秒级对齐；
   ② **窗口标题 == 该任务 `<Command>` 原文**（新控制台默认拿启动命令当标题、不含 Arguments）—— 最硬的一路；
   ③ 产物文件名里的秒级时间戳（如 `增量-YYYYMMDD-HHMMSS.md`）与命中时刻对上。
   三路一致才定案；若 ①③ 对上而机制看着不通，回去查 launcher 的 PE `Subsystem`，不要回头否定任务本身。

## 步骤

### 1. 盘点（一次拿到任务名 / 状态 / Action / 触发器类型）
```bash
export MSYS_NO_PATHCONV=1
powershell.exe -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-ScheduledTask | Where-Object {\$_.TaskPath -notlike '*Microsoft*'} | ForEach-Object { \$a=(\$_.Actions | ForEach-Object { \$_.Execute + ' ' + \$_.Arguments }) -join ' ;; '; '{0} | {1} | {2} | {3}' -f \$_.TaskName, \$_.State, \$a, ((\$_.Triggers | ForEach-Object { \$_.CimClass.CimClassName }) -join ',') }"
```
触发器类型速读：`MSFT_TaskTimeTrigger`（定时，看 `Interval`/`StartBoundary`）、`LogonTrigger`（登录即跑）、
`BootTrigger`（开机）、`RegistrationTrigger`（注册即跑）、`EventTrigger`、`SessionStateChangeTrigger`。

### 2. 判读会不会弹窗（读入口 exe 的 PE 头，不用跑起来看）

| Action 长什么样 | 弹窗？ | 机制 |
|---|---|---|
| `cmd /c ...`、`.bat`、`.ps1`、`.vbs` | **弹** | cmd.exe 是 console 子系统；交互式身份启动就必须分配可见控制台 |
| `python.exe ...` / `node.exe ...`（console 版） | **弹** | 同上 |
| `pythonw.exe ...` / `wscript //B //Nologo ...` / `powershell -WindowStyle Hidden` | **看 PE 头才知道** | 名字不算数，见下 |
| `conhost.exe` 被创建 | 不代表 | `CREATE_NO_WINDOW` 也建 conhost，但没有窗口 |

**★ 判据是 exe 的 PE `Subsystem`，不是它的文件名**：`Subsystem=3(CONSOLE)` 的程序被无控制台的
交互式身份启动时**必然**分配一个可见控制台；`Subsystem=2(GUI)` 才真的不弹。
`…\hermes-agent\venv\Scripts\pythonw.exe` 实测 `Subsystem=3`（uv 建的 redirector，名字带 w 照开控制台），
只有 uv 真实解释器目录下的 `pythonw.exe` 才是 2；`wscript.exe`/`cscript.exe` 恒为 2。
读法：`e = DWORD@0x3C`，`WORD@(e+24+68)` → 2=GUI，3=CONSOLE；批量体检用
`scripts/audit_scheduled_tasks.py`（导出全部任务 XML + 逐条 PE 判定，输出"会弹窗"清单）。
反直觉推论：**"脚本里零 `subprocess`/`Popen` 却固定每 N 分钟弹窗"并不矛盾** —— 弹窗来自 launcher
启动那一下，与脚本内容无关；**别用源码扫描去否定一个任务**（本机为此来回误判两次）。
另：`LogonType=SYSTEM/S4U/ServiceAccount` 或只有 `BootTrigger` ⇒ 会话 0，窗口不落用户桌面 → 直接排除。

### 3. 这个任务是什么（30 秒读懂用途，别猜）
1. 从 Action 抠出**脚本绝对路径**；2. 读脚本头部 docstring / `argparse` 的 help（用途、子命令、副作用）；
3. 看它的**产物目录**（日志 / `*_state.json` / `*.jsonl` / INBOX）判断真实干过什么、最后一次是什么时候。
4. 报告格式：任务名 + 频率 + 干什么 + 产物路径 + **当前状态**，一句话说清它为什么弹窗。

### 4. 还在跑吗（两处互钉，不看第三条）
```powershell
$i = Get-ScheduledTaskInfo -TaskName <任务名>; $i.LastRunTime; $i.NextRunTime; $i.LastTaskResult
```
- `LastRunTime` 与产物日志最后写入时间**一致** ⇒ 时间线可信；两处都停在几小时前 ⇒ 它不在跑，别再怀疑它。
- `LastTaskResult = 0` 只说明上次成功，不说明"正在跑"。
- 要跨触发点实测（每 2s 枚举**可见**控制台窗口 + 4688 审计 + 任务事件，跑完自动还原审计）：
  `pythonw scripts/console_flash_watch.py 25 <结果文件>`（本 skill 自带；采样窗口必须**跨过**被怀疑任务的触发点）。

### 5. 改入口（保留功能，去掉窗口）
把 Action 里的 `cmd /c <解释器> <脚本> ...` 换成隐藏外壳二选一：
- `pythonw.exe <脚本.py> ...` —— 仅当**那个** `pythonw.exe` 的 PE `Subsystem=2(GUI)` 时才成立；
  venv 里的往往是 3，换了等于白换（本机踩过）。不确定就用下面的 wscript 外壳。
- `wscript.exe //B //Nologo <外壳.vbs>` —— 跨解释器通用，外壳模板见 `templates/run_hidden.vbs`
  （`sh.Run cmd, 0, False`：窗口样式 0 = 隐藏，末参 False = 不等待）。
两种都**原样保留重定向与功能**，只是不再分配可见控制台。
VBS 外壳要点：**内容纯 ASCII**，含中文的路径全部从 `WScript.ScriptFullName` 反推；没有重定向需求就
别套 `cmd /c`，直接 `sh.Run """" & py & """ """ & script & """", 0, False`（不等待、继承环境与 CWD，
所以"命令原文等价改写"= 行为与原任务一致）。同机常有**多个同病任务**（创建者都以为 pythonw 静默），
一次体检全改完，别只修用户点名的那一个。
**改完必须回读**：`/Create /XML /F` 返回 0 **不代表定义已换**（管道/转码失败照样返回 0）→ 重新
`Export-ScheduledTask` 读回 `<Command>`/`<Arguments>`，并带上 `Get-ScheduledTaskInfo` 的
`LastRunTime/LastTaskResult/NextRunTime` 一起验。**还要验功能没坏**：手动用新外壳跑一次，看产物文件
新增 + 关联文件 mtime 刷新 —— `State=Ready / LastResult=0` 只说明调度器把它调起来了，不说明脚本还能干活。

### 6. 注册新的定时自动化（默认零弹窗）
入口用**已确认 `Subsystem=2(GUI)` 的解释器**，或 `wscript.exe` + VBS 外壳（§5）。
**不要想当然写 `pythonw.exe`**：venv 里的那个是 `Subsystem=3`，一样弹窗（先按 §2 验完再定）。
stdout/stderr 自己重定向到日志——
`pythonw` 下 `sys.stdout is None`，直接 `print` 会抛异常，脚本必须能无 stdout 运行（或 `stream.reconfigure(errors="replace")` 做兜底）。

#### 6.1 等一个「不知道何时恢复」的窗口：错开的一次性探针
场景:远端限流/封禁只告诉你「N 小时后解封」,而你现在就想挂机。做法 = 挂**几档错开的一次性任务**,醒来直接看日志:
```bash
T='C:\<工作区>\run_probe.bat'   # 路径无空格 ⇒ /TR 直接给 .bat 绝对路径最省事
for ST in 06:10 09:10 12:10; do
  MSYS_NO_PATHCONV=1 schtasks /Create /F /SC ONCE /ST "$ST" /SD 26/09/2026 /TN "probe_${ST/:/}" /TR "$T"
done
```
- ★ **`/SD` 跟系统区域走**：中文区域必须 `dd/mm/yyyy`,写成 `yyyy/mm/dd` 会直接报「无效开始日期」(日期格式应该是 dd/mm/yyyy)。`/ST` 用 24h `HH:MM`。
- `.bat` 包一层: `cd /d <工作区>` + `set` 需要的 env(代理/会话名) + `echo ==== %DATE% %TIME% ==== >> log` + `python -u x.py >> log 2>&1`;bat 里别用 label/goto(LF-only 换行才安全),路径含空格的目录先搬出来。
- 验证不看 schtasks 的中文输出(GBK,`grep` 会整片漏),用 `Get-ScheduledTask -TaskName 'probe_*' | Select-Object TaskName,State` 看 `State=Ready`。
- **跑完收尾**:`schtasks /Delete /TN <名> /F`——一次性探针不删会一直留在盘点清单里(§1 会把它当「可疑任务」查半天)。
- 探针脚本自身要**撞限流就整体退出**(打印 `e.seconds` 并 `return`),别在循环里继续撞:挂机任务的产物是给醒来的人看的,不是拿来烧额度的。

## Pitfalls
1. **`schtasks /query /fo LIST /v` 与 `/fo CSV /v` 在中文系统输出 GBK**：`grep` 整片漏（只回一行 `Binary file matches`），
   awk 按 `","` 切 CSV 列也不稳。**一律用 PowerShell `Get-ScheduledTask` + `[Console]::OutputEncoding=[Text.Encoding]::UTF8`**，
   过滤在 PowerShell 里 `Where-Object` 做。
2. **`State=Disabled` 的任务照样有 `NextRunTime`**（残留计算值）——只认 `State` + `LastRunTime`。
3. `Microsoft-Windows-TaskScheduler/Operational` 日志**默认未启用**（`IsEnabled=False`、RecordCount 空）：
   查不到任务历史是正常的，别死磕，回退到 LastRunTime + 产物 mtime。
4. **Prefetch 不可信**：`C:\Windows\Prefetch\*.pf` 在 SSD 上常被禁用或按 hash 分文件，
   会出现"任务明确跑过、pf 却是几个月前"的假象——不用它判断程序最近有没有运行。
5. 别在大目录（上万文件的项目库）上跑递归 `grep -rl`：必超时或被 hardline 拦。先 `ls` 定位子目录或改用 `search_files`。
6. 别把"看起来可疑"直接写进结论：先核对归属（任务 Author/Description、脚本所在目录、产物路径），
   一个每 30 分钟的任务可能只是某项目的自监控哨兵，不是恶意程序。
7. **改任务定义不要从命令行传中文路径**（bash→powershell 的编码链会毁掉它）。安全姿势：
   `Export-ScheduledTask -TaskName '<名>' | Out-File -Encoding Unicode '<ascii路径>.xml'`
   → Python 改 XML 里的 `<Command>`/`<Arguments>`（以 `encoding='utf-16'` 写回）
   → `schtasks /Create /TN '<名>' /XML '<ascii路径>.xml' /F`（整份覆盖，Triggers/Principal 来自 XML）。
   **导入前先备份原 XML，报告里给出那条回滚命令。**
8. **要触发含中文路径的 exe**（如 `wscript "<中文目录>\x.vbs"`）**从 Python `subprocess` 传参**（走 Unicode API）；
   经 bash 命令行传会被按 ANSI 解码 → 找不到文件。PowerShell 取回的文本也一律 `Out-File -Encoding UTF8`
   落文件再 read_file，不要经 bash 管道读中文。
9. **等几十分钟后的触发点**：前台 terminal 约 420s 上限，`sleep` 必中途超时 → 用**后台**
   `sleep N && verify.py` 配 `notify_on_complete`；复核脚本自己把结论写文件（pythonw 下无 stdout），
   采集时刻要落在触发点之后，别正好压在触发瞬间。

## 一句话总结
定时弹窗 = 计划任务在拉 console 程序；**先 `Get-ScheduledTask` 盘 Action，再读入口 exe 的 PE `Subsystem`**
（`cmd`/`.bat`/`powershell` 恒 3=弹，`wscript` 恒 2=安全；**`pythonw.exe` 这个名字不算数**，venv 里的实测是 3），
用 `LastRunTime` + 产物日志 mtime 互钉证明它还在不在跑，改入口（不砍功能）去掉窗，全程系统级改动先获同意。
