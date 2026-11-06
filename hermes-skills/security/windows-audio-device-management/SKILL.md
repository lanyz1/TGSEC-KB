---
name: windows-audio-device-management
description: >-
  测绘引擎·Use when switching Windows audio output devices.
owned: true
tier: general
pack: survey-skill
---

# windows-audio-device-management（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-audio-device-management/`

溯源（仅标记）：`hermes/software-development`

---

# Windows Audio Device Management

切换/查询 Windows 音频输出设备、按应用指定输出、排查"声音从错误的设备出来"。

## When to use
- 用户说"把X(酷狗/QQ音乐/浏览器)的输出改成耳机/音箱"、"耳机没声音"、"声音从扬声器出来"
- 需要知道当前默认播放设备 / 系统有哪些音频端点
- 需要给单个应用指定独立输出设备

## Step 1 — 枚举音频端点 (UTF-8 防乱码)
```powershell
powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-PnpDevice -Class AudioEndpoint -Status OK | Select-Object FriendlyName, InstanceId | Format-List"
```
- Render 端点的 InstanceId 含 `{0.0.0.00000000}.{...}`；Record/捕获端点含 `{0.0.1.00000000}`。
- **蓝牙耳机通常暴露两个端点**：`扬声器 (xxx)` 与 `头戴式耳机 (xxx Hands-Free)` —— 听歌选前者（非 Hands-Free）；Hands-Free 是通话模式，音质差。
- 常见设备：kX 10k1 声卡（多个 Wave Out + Master Mixer + SPDIF）、网易/腾讯虚拟音频、NVIDIA 虚拟音频。Realtek/HDMI 在 `Win32_SoundDevice` 里 `ConfigManagerErrorCode=22` = 被禁用（有独立声卡时正常，不是故障）。

## Step 2 — 查询当前默认输出设备
用 `scripts/query_audio_endpoints.cs`（CoreAudio IMMDeviceEnumerator）输出 `DEFAULT_OUTPUT=` 与全部活动 Render 端点名+ID。编译运行：
```powershell
powershell -NoProfile -Command "Add-Type -Path 'C:\path\query_audio_endpoints.cs' -OutputAssembly 'C:\path\query_audio_endpoints.exe' -OutputType ConsoleApplication; & 'C:\path\query_audio_endpoints.exe'"
```
⚠ Add-Type 传位置参数（`Add-Type 'file.cs'`）会把路径当源码文本 → `Unrecognized escape sequence`。必须用 `-Path`。

## Step 3 — 改输出设备（按可靠性排序）
1. **全局默认输出**：任务栏喇叭图标 → 选择设备；或 `Start-Process 'ms-settings:sound'`。
2. **按应用指定 (Win11，首选)**：`Start-Process 'ms-settings:apps-volume'` → 音量混合器 → 找到目标应用 → 输出设备下拉选耳机。系统级原生，不依赖应用自身 UI，最可靠。
3. **应用内设置**：音乐类应用 → 设置 → 音频设置/输出设备。酷狗路径见 `references/kugou-audio-output.md`。**自绘UI应用（酷狗等）自动化点击不稳定，优先系统级方案**。

## Step 4 — 验证
- 重新播放/重启应用再听。酷狗会提示"新设置将在重新播放时生效"。
- 可重跑 query 脚本确认 `DEFAULT_OUTPUT` 已变化。

## Pitfalls
- PowerShell 输出中文设备名乱码 → 必须 `[Console]::OutputEncoding=[Text.Encoding]::UTF8`。
- 后台自动化点击自绘UI应用（酷狗/QQ音乐）坐标易失准：窗口移动后坐标全部失效，元素索引在 Cua Driver 0.17 下需 token/snapshot_id。优先走系统级方案。
- 改完"没生效"通常不是缓存问题，而是音频会话未重建 → 切歌或重启应用。

## Support files
- `scripts/query_audio_endpoints.cs` — CoreAudio 查询默认输出 + 全部活动端点（名字+ID+状态）
- `references/kugou-audio-output.md` — 酷狗音频输出设置路径 + 自绘UI自动化实测记录（坐标系统、窗口漂移、Cua 0.17 限制）
