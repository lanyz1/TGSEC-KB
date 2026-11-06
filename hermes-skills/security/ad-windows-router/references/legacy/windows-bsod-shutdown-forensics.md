<!-- archived from /root/.hermes/skills/security/windows-bsod-shutdown-forensics/SKILL.md on 2026-10-21 -->

---
name: windows-bsod-shutdown-forensics
description: Use when 查电脑何时关机/重启或蓝屏原因. 事件时间线→minidump 解析→归因到具体驱动+时间戳关联.
---

> 归档卡：原目录 `/root/.hermes/skills/security/windows-bsod-shutdown-forensics`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/windows-bsod-shutdown-forensics/…')`，不要相对 `references/legacy/` 解析。

# Windows 蓝屏 / 异常关机重启 诊断

## 何时用
- 「我的电脑什么时候关机/重启了」「为什么突然重启/黑屏/蓝屏」「昨晚是不是崩过」
- 需要把一次关机定性成：计划内关机（用户/更新发起） vs 蓝屏崩溃 vs 断电/硬复位

## 交付标准（用户偏好）
- 聊天里**先结论后证据**：时间线表（时刻 / 🔴异常🟢干净 / 说明）+ 根因 + 证据 + 处置建议。
- 归因要到**具体驱动名 + 模块内偏移**，不许收在「可能是驱动问题」。
- 证据分级：调用栈帧归属 > 样本文件时间戳 > 崩溃时进程列表 > 猜测；不确定写「嫌疑」不写「确定」。
- 同时落一份 md 到 `C:\Users\Administrator\Desktop\电脑蓝屏崩溃诊断_<yyyymmdd>.md`，聊天里用 `MEDIA:<绝对路径>` 附上；报告必须带「取证命令」段，便于复核。
- 建议要给可执行动作（修复/卸载具体组件、`mdsched.exe`、`chkdsk C: /scan`、更新显卡驱动），并主动问是否要 WinDbg 符号级定位。

## Step 1 时间线与性质判定
```powershell
# 开机时间与运行时长
Get-CimInstance Win32_OperatingSystem | Select-Object LastBootUpTime,Caption,Version
# 关机/重启/异常事件（升序看历史，降序看最近）
Get-WinEvent -FilterHashtable @{LogName='System'; ID=41,1074,6005,6006,6008,1076} -MaxEvents 60 |
  Select-Object TimeCreated,Id,ProviderName | Format-Table -AutoSize
# 蓝屏历史：只有这条能证明是蓝屏，且带 bugcheck 参数 + dump 路径
Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001} -MaxEvents 20 |
  ForEach-Object { $_.TimeCreated; $_.Message }
```
| 事件 | 含义 |
|---|---|
| 6005 / 6006 | 日志服务启 / 停 → 一次**干净**开关机 |
| 1074 | 有进程发起的关机/重启（开始菜单、更新）→ 计划内 |
| 41 | 上次关机不干净（蓝屏 / 断电 / 长按电源键 / 死机硬复位） |
| 6008 | 上次关机是「意外」的，附最后一次心跳时刻 |
| 1001 | WER 记录 bugcheck 参数 + dump 路径 → **判蓝屏的唯一硬证据** |

**核心鉴别**：41 且有配套 1001 = 蓝屏；41 而无 1001 = 断电/硬复位/挂死后强制关机 → 结论往硬件（内存/电源/过热）走，**别写成蓝屏**。历史上多是 41 无 1001 的机器，怀疑面要同时含硬件。

## Step 2 蓝屏取证与转储解析
- dump 在 `C:\Windows\Minidump\*.dmp`；Windows 默认小内存转储（~5MB）且**只保留最近一两次，旧 dump 会被轮换** → 事故后第一时间复制出来再分析。
- 现成脚本：`python scripts/minidump_analyze.py <dmp> [--stack]`（纯 stdlib，无需 WinDbg）打印 bugcheck+参数、模块表(名/基址/大小)、把崩溃地址与每个栈帧归属到模块、未加载驱动名。
- **自检**：解析出的模块数 == TRIAGE 的 DriverCount（例：245/245 全部解析出名字）且崩溃地址落在 ntoskrnl 区间 = 解析正确；解析不出名字说明 stride/字段偏移不对，见 `references/minidump-internals.md` 的备用 stride。
- 只有需要**函数名级**定位才上 WinDbg + 微软符号服务器（要下符号包，先问用户）。
- 别在 `kdmp-parser`(pip) 上耗时间：它只吃 full memory dump，不认 small memory dump。

## Step 3 归因：把栈帧变成驱动名
1. **栈帧直方图** — 多数帧落在哪个第三方 `.sys`，它就是嫌疑驱动（实测常见：反作弊 `ACE-ADVT.sys` 15 帧 / ntoskrnl 49 帧）。
2. **时间戳关联** — 把嫌疑驱动的文件时间与崩溃日期对齐（`Get-ChildItem C:\Windows\System32\drivers\*.sys` + 厂商安装目录如 `C:\Program Files\<vendor>\`）。反作弊/杀软/加速器会**热更新内核驱动**：当天更新的驱动 + 当天崩溃 = 强嫌疑。
3. **进程列表** — dump 内含崩溃瞬间的进程名（脚本已覆盖；或 `grep -ao '[A-Za-z0-9_.-]*\.exe' dump`），能说明当时在跑什么（游戏/加速器/远控）。
4. **反向排除** — `verifier /query`（`No drivers are currently verified.` = 没开驱动验证器，不是它）；`C:\ProgramData\Microsoft\Windows\WER\ReportArchive` 找历史 `VerifierFailure`/`AppCrash`；`C:\Windows\LiveKernelReports` 找 TDR/显卡类转储。
5. **无 dump 的老崩溃**（只有 41/6008）只能给「断电/硬件」+ 旁证建议（内存诊断、chkdsk、显示驱动事件 153/nvlddmkm）。

## Pitfalls
- 输出中文事件消息必须 `[Console]::OutputEncoding=[Text.Encoding]::UTF8`，否则全是乱码。
- git-bash 里调 PowerShell：`powershell.exe -NoProfile -Command '...'` 用 **bash 单引号**包住、PowerShell 内部用双引号；反引号会被 bash 当命令替换吃掉，`$_`/`${}` 也可能被展开。
- 解析与多字段查询写成**脚本文件再跑**（`write_file` → `python x.py`），长内联命令易被截断，输出被压缩后看到的可能不是真实结果。
- 事件查询 exit code 1 往往只是「无匹配事件」（例如该机没有 6008 记录），不是脚本坏了；先怀疑过滤条件过窄。
- 6008 报的崩溃时刻来自最后一次心跳/日志写入，可能比真实掉线**早几分钟** → 用数据文件 mtime、应用日志尾部交叉校正，报告里给时间窗而不是单点。
- 中文环境事件时间显示 `dd/MM/yyyy`，别读成 yyyy-mm-dd。
- 报告里区分「本次根因」与「其他独立问题」（如 nvlddmkm TDR、历史上的 0x4E PFN_LIST_CORRUPT），不要混成一条因果链。

## 参考
- `references/minidump-internals.md` — DUMP_HEADER64 / TRIAGE_DUMP64 / DUMP_DRIVER_ENTRY / 字符串池 字段偏移、备用 stride 与自检方法。
- `scripts/minidump_analyze.py` — 无 WinDbg 解析 small memory dump 的现成脚本。
