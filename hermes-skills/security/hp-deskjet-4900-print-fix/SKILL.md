---
name: hp-deskjet-4900-print-fix
description: >-
  测绘引擎·Use when HP Deskjet 4900 print fails. IPP driver broken.
owned: true
tier: general
pack: survey-skill
---

# hp-deskjet-4900-print-fix（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/hp-deskjet-4900-print-fix/`

溯源（仅标记）：`hermes/hp-deskjet-4900-print-fix`

---

## When to Use

Trigger when: HP DeskJet 4900 series 在这台 Win11 电脑上打印失败(任务卡 0 页 / 假完成 / 白纸 / 打一半停),或用户提到该打印机驱动问题。先读"已实锤结论",别重复已排除的方向(v2rayN、删打印机重建、HPPSdr 修复)。

# HP DeskJet 4900 + Win11 打印修复

## 已实锤结论(2026-08-18 排查)
- 本机 **Windows 打印通道坏**:Microsoft IPP Class Driver 与 HP DeskJet 4900 通信失败
- 症状:任务卡 "Printing, Retained" 0 页 / 假完成 / 白纸 / 打一半停;打印机状态常显示 Normal 但不出纸
- **打印机硬件 100% 正常**:自检页(拔 USB → 按住绿色三角"恢复"键不放 → 按电源开机 → 松手)完整打出;在别的电脑(装 HP 原厂驱动)可正常打印
- **HPPSdr 工具自己的打印通道可用**(绕过 IPP 驱动);`rundll32 printui.dll,PrintUIEntry /k /n "HP DeskJet 4900 series"` 走 IPP 永远坏(0 页 Error)
- v2rayN 开/关**不影响** IPP 假完成(曾误判;用户"关 v2 后测试页正常"实际是 HPPSdr 通道)
- 删打印机实例(Remove-Printer)+ Add-Printer 重建 = 无效,且用户会认为"驱动被搞坏"——**删/禁设备前必须先征得同意**

## 关键路径/链接
- HP Print and Scan Doctor 正确页面:`https://support.hp.com/cn-zh/topic/hp-print-scan-doctor`(**help/** 开头是 404,页面 JS 动态加载,程序化抓不到直链)
- 错误工具:`sp173774.exe` 是 HP Support Assistant(186MB);HPPSdr.exe 约 12MB
- HPPSdr 流程:选打印机 → 开始 → 修复;修复后驱动**仍为 IPP**(HPPSdr 不换驱动)

## 下一步修复方案(未完成,待用户从可用电脑导驱动)
1. 在能用的那台电脑导出 HP 驱动:PowerShell `pnputil /export-driver` 或复制 `C:\Windows\System32\DriverStore\FileRepository\*hp*` 到本机
2. 本机 `pnputil /add-driver xxx.inf /install`
3. 切换:`Set-Printer -Name 'HP DeskJet 4900 series' -DriverName '<HP驱动名>'`
4. 验证:`rundll32 printui.dll,PrintUIEntry /k /n "HP DeskJet 4900 series"`
- 注:Win11 驱动库里的 `hp_dj_2800_4900.inf` 只是 HPPSA stub(50 行,非打印驱动);Windows Update Catalog 无 4900 驱动

## 本机打印环境
- 打印机:HP DeskJet 4900 series,端口 USB001,设备 `USBPRINT\HPDESKJET_4900_SERIES`,USB VID_03F0&PID_041B
- 驱动:Microsoft IPP Class Driver(唯一可用,系统组件,别删)
- WPS COM 注册在 **HKCU**(Word.Application / KWPS.Application 均可 `New-Object -ComObject Word.Application`),HKLM 查不到
- 打印 docx 脚本:COM → `Documents.Open($path, $false, $true)` → `PrintOut()` → `Close(0)`;打开失败返回 null 需重试 2-3 次(用 UTF-16LE Base64 EncodedCommand 传中文路径)

## 坑
- `pnputil /disable-device` 首次可用,后续报 "not supported on this OS product" → 改用 `Disable-PnpDevice`/`Enable-PnpDevice`(偶发 Generic failure,重试或让用户拔插 USB)
- 连续发任务偶现"第一个卡、第二个成功"模式,不代表稳定
- 打印任务会互相堵,先 `Get-PrintJob | Remove-PrintJob` 清队列再发
- 打印机属性/状态查询:`Get-Printer -Name 'HP DeskJet 4900 series' | fl PrinterStatus,JobCount`
