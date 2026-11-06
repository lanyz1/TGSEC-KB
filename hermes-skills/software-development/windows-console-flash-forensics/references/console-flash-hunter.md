name: console_flash_hunter
summary: 闪窗取证抓捕器——定位"定时/随机弹 cmd 黑窗"来源的双证据工具
location: D:\测绘引擎\tools\ops\console_flash_hunter.py

## 何时用
用户报"屏幕时不时弹一个黑窗/cmd 窗口一闪而过"，且已排除明显嫌疑时。
它给出**两路证据**：
1. 可见控制台窗口（类名 + 标题 + 宿主 pid）—— 每 0.4s 采样
2. 进程表全量命令行 + 父子关系（PID|PPID|Name|CommandLine）—— 每 2.5s 采样
时间对齐后，"窗口命中时刻" 对应的 "新进程命令行" 就是元凶。

## 用法
```bash
# 务必 pythonw.exe 启动（否则自己的控制台污染观测）
"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe" \
  "D:\测绘引擎\tools\ops\console_flash_hunter.py" --minutes 20 \
  --out "D:\tmp\flash.txt"
```
参数：`--minutes`（默认 20）、`--out`（默认 %TEMP%\console_flash_report.txt）。
窗口命中是**实时落盘**的（line-buffered），所以即便中途崩了也有证据。

## 定位流程（先查计划任务，再上抓捕器）
1. 列非微软计划任务，找 `<Command>` 是 console 程序（cmd/powershell/bat）且 Principal 为
   `InteractiveToken` 的项：
   ```powershell
   Get-ScheduledTask | Where-Object {$_.TaskPath -notlike '*Microsoft*'} | ForEach-Object {
     $a=($_.Actions|ForEach-Object{$_.Execute+' '+$_.Arguments}) -join ' ;; '
     '{0} | {1} | {2}' -f $_.TaskName,$_.State,$a }
   ```
   —— **判据**：`LogonType=ServiceAccount`(SYSTEM) 的窗口不落用户桌面（排除）；
   `wscript.exe` / `pythonw.exe` 入口 + 内部不 spawn 子进程 → 不弹窗（排除）；
   `cmd`/`.bat`/`powershell` + `Interactive` → 会弹。
2. 交叉验证：任务 `LastRunTime` 与 `task.log` 的 mtime 对齐（证明它确实在跑）。
3. 只在"排除不掉"或"有可疑但不匹配"时才上抓捕器，跑够覆盖 2–3 个触发周期。

## 坑（每条都踩过）
- **窗口类名白名单必须三个全带**：`ConsoleWindowClass` / `CASCADIA_HOSTING_WINDOW_CLASS` /
  `cygwin-console-helper`。Win11 默认终端 = Windows Terminal 时，新控制台窗口类名是 `CASCADIA_*`，
  只查 ConsoleWindowClass → "0 个窗口" 的**假阴性**。
- **对照实验的靶子禁用 `timeout N`**：ConPTY 下因 stdin 非真控制台而秒退，窗口来不及出现，
  会得出错误结论。**用 `ping -n N` 保活**（`subprocess.Popen(["cmd","/c","ping","-n","20","127.0.0.1"], creationflags=subprocess.CREATE_NEW_CONSOLE)`）。
- **必须做正对照**：`sh.Run(cmd, 1, ...)` 应捕获 ≥1 窗口，`sh.Run(cmd, 0, ...)` 应 0 个。
  正对照有、反对照无 → 才算证明；只有"0 命中"无法排除工具失效。
- 抓捕器自己调 powershell 一律加 `CREATE_NO_WINDOW (0x08000000)`。
- **`.ps1` 文件必须纯 ASCII**：PowerShell 5.1 默认按 ANSI(GBK) 读脚本，UTF-8 无 BOM 的中文
  会吞掉引号 → `TerminatorExpectedAtEndOfString`。要么写 BOM，要么全英文。
- `schtasks /query` 输出 GBK，`grep` 中文任务名必失败 → 一律用 PowerShell `Get-ScheduledTask`。
- 纯 Python 脚本（pythonw 跑）**不会**产生控制台窗口；只有 spawn 出 console 子进程或入口本身是
  cmd 才会。判"某任务是否弹窗"要连它 spawn 的子进程一起看。
