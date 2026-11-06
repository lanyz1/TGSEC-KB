# Windows/git-bash 本机运维坑（实测）

> 都是“静默失败”型坑：不报错、结果错。写脚本前先扫一眼。

## 1. 路径：原生程序只认 `D:/...`
- Python / node / curl / 7z / git 等**原生程序不认 MSYS 的 `/d/渗透/...`**：`open("/d/x.txt")` 会静默不存在或不匹配 ⇒ 词表/字典只加载到一部分（实测：13k 字典只进 1.2k，另两个文件被静默跳过）。
- 规矩：脚本里写 `D:/...`（正斜杠原生路径）；只有 bash 内建（`cd`、`[ -f ]`）才认 `/d/...`。
- 排查法：加载后**打印去重后的条数**，与 `wc -l` 对账。

## 2. PowerShell 脚本必须纯 ASCII
- `powershell -File x.ps1` 会按 **GBK** 读 UTF-8 文件 ⇒ 中文让字符串终止符错位，报 `缺少终止符`/`TerminatorExpectedAtEndOfString`，整脚本不执行。
- 规矩：`.ps1` 一律英文/ASCII 输出；要中文就在调用方（bash/python）里打印。

## 3. 杀进程树：别用 bash kill，也别把复核串写进自己的命令行
- `kill` 只杀外壳，Python 子进程存活 ⇒ 用 PowerShell：
  `Get-CimInstance Win32_Process | ? { $_.CommandLine -match '<脚本名>' } | % { Stop-Process -Id $_.ProcessId -Force }`
- **两侧都要过滤 `Name`**：
  - 杀：先 `Name -like 'python*'` 再匹配 CommandLine（否则把 `tee.exe`、无关 bash 一起带走）。
  - 复核：**只统计 `Name -like 'python*'`** —— 复核命令自身的命令行里含匹配串，会把当前终端外壳误报成“ALIVE”。
- 杀 `bash.exe` 树会**连带杀掉当前终端会话**（表现为工具调用异常退出）⇒ 复核要另起一次调用。
- 复核口径：`0 case-job python processes` + 我方日志 mtime 不再增长 = 真停。

## 4. 语法体检不要用 `cfile=os.devnull`
- `py_compile.compile(f, cfile=os.devnull)` 在 Windows 报 `nul is a non-regular file` ⇒ 批量体检会得到**全量假失败**（实测 412/415 全“失败”）。
- 正确：纯内存编译 —— `compile(open(f,encoding='utf-8').read(), f, 'exec')`，捕获 `SyntaxError`/异常。

## 5. 长循环作业的稳定性
- 本机代理（v2rayN/clash 等）在**多作业并发**下会瞬时断连，`ProxyError: RemoteDisconnected` 直接把长任务打死 ⇒ 目标站可直连时一律 `UG_DIRECT=1`/` trust_env=False` 走直连 + 失败重试 + 断点续跑（状态写 JSON，重跑自动接续）。
