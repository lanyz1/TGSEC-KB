# 计划任务黑窗：根因体检 + 全系统排查 + 隐藏外壳修法

从"定时弹 cmd 黑窗"定位到**任务计划程序**之后的完整作业流程。本机实测（2026-09-22）走过一遍，结论已用前后对照证死。

---

## 1. 第一根因：`pythonw.exe` 可能根本就是 CONSOLE 程序

**别再靠文件名判断**。`venv\Scripts\pythonw.exe`（uv 装的 redirector）在 PE 头里是 **Subsystem=3 (CONSOLE)**，名字带 w 却会分配控制台窗口。实测：

| 文件 | Subsystem | 后果 |
|---|---|---|
| `hermes-agent\venv\Scripts\pythonw.exe` | **3 = CONSOLE** | 从任务计划启动 → 必弹窗 |
| `hermes-agent\venv\Scripts\python.exe` | 3 = CONSOLE | 同上 |
| `uv\python\cpython-3.11-*\pythonw.exe` | 2 = GUI | 真·无窗口 |
| `wscript.exe` / `cscript.exe` | 2 = GUI | 可用作隐藏外壳 |
| `cmd.exe` / `powershell.exe` | 3 = CONSOLE | 会弹 |

**判定代码**（不要猜，直接读 PE 头）：

```python
import struct, os

def pe_subsystem(path):
    p = path.strip('"')
    if not os.path.exists(p):
        return None, "missing"      # 无路径的裸名(如 wscript.exe)会落这里，属正常
    with open(p, "rb") as f:
        data = f.read(0x800)
    if data[:2] != b"MZ":
        return None, "notpe"
    e = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e:e+4] != b"PE\0\0":
        return None, "nosig"
    sub = struct.unpack_from("<H", data, e + 24 + 68)[0]
    return sub, {2: "GUI", 3: "CONSOLE", 1: "NATIVE"}.get(sub, "?")
```

> 教训：曾据"脚本源码零 `subprocess`/`Popen`/`os.system`"判定该任务静默 —— **推理方向就是错的**。黑窗不是子进程造成的，是**它自己启动那一下**造成的。源码审查证明不了"不弹窗"。

## 2. 全系统体检：一次找出所有会弹窗的任务

不要一个个试。导出全部任务 XML，程序化判定。

**Step 1 — 导出**（`.ps1` 必须**纯 ASCII**，PS 5.1 按 ANSI/GBK 读脚本，含 UTF-8 中文会吞引号导致语法崩）：

```powershell
$dir = 'C:\Users\<user>\AppData\Local\Temp\taskxml'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Get-ChildItem $dir | Remove-Item -Force
$i = 0
foreach ($t in (Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '*Microsoft*' })) {
    $i++
    $x = Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath
    if ($x) {
        $name = ('{0:d2}_' -f $i) + ($t.TaskName -replace '[\\/:*?"<>|]', '_')
        $x | Out-File -Encoding Unicode (Join-Path $dir ($name + '.xml'))
    }
}
Write-Output ("dumped {0} tasks" -f $i)
```

**Step 2 — 判定**：读每个 XML（UTF-16），取 `<Command>`/`<Arguments>`/`<LogonType>`/触发器，对 Command 做 PE 检查。

**弹窗条件（两条同时成立）**：
1. Command 指向 **CONSOLE** 子系统程序（或 `cmd /c`、`powershell`、裸 `.bat`）
2. `LogonType` = **InteractiveToken**（空值也按交互算）

**自动排除**：
- `LogonType` = `S4U` / `ServiceAccount` / `Password` → 非交互会话，窗口不落用户桌面
- `UserId` = `S-1-5-18`（SYSTEM）+ BootTrigger → 会话 0 隔离，不可见
- Command = `wscript.exe` / GUI 程序（Subsystem=2）
- 无触发器（仅手动/服务调用）

本机实测：32 个任务里只有 3 个命中（2 个定时任务 + 1 个 SYSTEM 开机任务被排除）。**频率要对齐现象**——用户"每隔 15 分钟"被弹一次，实际是 `:13/:43` 与 `:08/:38` **两个任务交替**，不是单个任务每 15 分钟。

## 3. 修法：wscript + VBS 隐藏外壳（原命令一字不改）

`wscript.exe` 是 GUI 子系统（本身不开控制台），`WScript.Shell.Run` 的第二个参数 `0` = `SW_HIDE`，被拉起的 console 程序**窗口从不显示**（不是"显示了再隐藏"，实测零闪现）。

**模板**（内容**纯 ASCII**，路径一律从 VBS 自身位置反推 —— 这样脚本放在任何中文目录里都不用写中文字面量）：

```vbs
Option Explicit
Dim fso, sh, here, py, script, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

here   = fso.GetParentFolderName(WScript.ScriptFullName)
script = here & "\sync_engine.py"
py     = "C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"

If Not fso.FileExists(script) Then WScript.Quit 2
If Not fso.FileExists(py)     Then WScript.Quit 3

cmd = """" & py & """ """ & script & """"
sh.Run cmd, 0, False          ' 0 = SW_HIDE, False = 不等待
```

**改任务定义**（PowerShell 权威，别用 `schtasks /query` 文本解析）：
1. `Export-ScheduledTask -TaskName <n> | Out-File -Encoding Unicode <bak>.xml`（备份 = 回滚源）
2. 程序改 XML：`<Command>` → `wscript.exe`，`<Arguments>` → `//B //Nologo "<vbs绝对路径>"`，写回 **UTF-16**
3. `schtasks /Create /TN "<n>" /XML "<new>.xml" /F`
4. **不要在命令行里传中文路径**（bash→native exe 按 GBK 解读会乱码）→ 备份/新 XML 走**纯 ASCII 路径**（如 `%TEMP%`），再用 Python 分发到中文目录

**回滚（一条）**：`schtasks /Create /TN "<n>" /XML "<bak>.xml" /F`

## 4. 验证纪律（这一节最容易骗自己）

- **`LastTaskResult = 0` 不能证明脚本跑了**：VBS 是 fire-and-forget（`sh.Run ..., False` 立即返回），0 只是 `wscript.exe` 的退出码。**必须查文件级证据**：日志文件 mtime + 新增日志行、产物文件 mtime。
- **"没有产物" ≠ "没跑"**：被监控程序往往**只在检测到变更时落盘**（本机 sync 在"无变更"轮里不写增量文件，日志里那几轮 INBOX 也确实空缺）。判读前先看它自己的日志。
- **必须有前后对照**：同一任务、同一观测器、同一触发方式，**唯一变量是入口**。本机：旧入口 `:08/:38` 两轮各抓到 2 个窗；换 `wscript`+VBS 后 `:38` 那轮 0 命中 —— 这样结论才站得住。
- 观测器用 `pythonw.exe` 启动避免自污染，且**自己调 powershell/tasklist 一律加 `CREATE_NO_WINDOW`**。
- 窗口类名白名单三全：`ConsoleWindowClass` / `CASCADIA_HOSTING_WINDOW_CLASS` / `cygwin-console-helper`（默认终端为 Windows Terminal 时新控制台是 `CASCADIA_*`）。
- 手工正对照触发时，用 **Python `subprocess` 传 Unicode 参数**调 `wscript.exe`（bash 直接调会让中文 VBS 路径乱码）；VBS 内 `sh.Run` 用 `False`，脚本在后台跑，随后比对产物 mtime。

## 5. 环境坑速查

| 坑 | 表现 | 处理 |
|---|---|---|
| `.ps1` 含中文 | `powershell -File` exit 1，报语法错 | 脚本改纯 ASCII；中文数据用 `Out-File -Encoding UTF8` 落文件再给 Python 读 |
| `iconv` | ``iconv: command not found`` | 本机 git-bash 没有，别用；直接输出到文件用 Python 解码 |
| `schtasks` 文本输出 | 中文任务名乱码/匹配为空 | 一律 `Get-ScheduledTask` / `Export-ScheduledTask` |
| 命令行中文路径 | 中文参数传给 native exe 乱码 | 走 ASCII 中间路径 + Python 分发 |
| 全盘 `grep -rl` | exit 124 超时 | 限定目录，或用 Python `os.walk` |
| 任务计划操作日志 | `Microsoft-Windows-TaskScheduler/Operational` `Enabled=False` | 取不到历史 → 改走 `LastRunTime` + 产物 mtime + 自建窗口观测器 |
