<!-- archived from /root/.hermes/skills/security/windows-software-audit/SKILL.md on 2026-10-21 -->

---
name: windows-software-audit
description: >-
  测绘引擎·Comprehensive software inventory on Windows and Linux migration compatibility
  assessment. Uses winget list, registry queries, start menu inspection, and dev tool
  package managers to build a complete picture of installed apps.
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/windows-software-audit`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/windows-software-audit/…')`，不要相对 `references/legacy/` 解析。

# windows-software-audit（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-software-audit/`

溯源（仅标记）：`hermes/software-development`

---

# Windows Software Audit

## Overview

Three-source approach to get the full picture of installed software on Windows. Single-source methods miss things — winget misses MSIX apps, registry misses portable apps, start menu misses CLI tools. Always use all three, then cross-reference.

## Source 1: winget list

Fastest and most structured. Lists most desktop apps, MSIX packages, and winget-managed tools.

```bash
winget list
```

## Source 2: Windows Registry

Catches everything with a proper installer (exe/msi) including legacy 32-bit apps (WoW64).

```powershell
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Where-Object { $_.DisplayName } | Select-Object DisplayName, DisplayVersion, Publisher

Get-ItemProperty HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Where-Object { $_.DisplayName } | Select-Object DisplayName, DisplayVersion, Publisher

Get-ItemProperty HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Where-Object { $_.DisplayName } | Select-Object DisplayName, DisplayVersion, Publisher
```

## Source 3: Start Menu

Catches portable apps and shortcuts that don't register in winget or registry.

```bash
ls "/c/ProgramData/Microsoft/Windows/Start Menu/Programs/"
ls "/c/Users/$(whoami)/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/"
```

## Source 4: Developer Tool Package Managers

```bash
scoop list 2>/dev/null || echo "no scoop"
choco list --local-only 2>/dev/null || echo "no choco"
pip list --format=columns 2>/dev/null | head -30
npm ls -g --depth=0 2>/dev/null
uv tool list 2>/dev/null || echo "no uv tools"
```

## Linux Compatibility Assessment

### Category A: Native Linux Support

Apps with official Linux builds: Google Chrome, Microsoft Edge, Firefox, Git, Node.js, Python, FFmpeg, Telegram Desktop, WPS Office, Cursor/VSCode, WeChat, QQ, Baidu Netdisk, ToDesk, Sunflower Remote, Docker, Spotify, Discord, Slack, Obsidian.

### Category B: Available via Alternative

| Windows App | Linux Alternative |
|-------------|------------------|
| Everything | plocate / fsearch / fd-find |
| GPU-Z | nvtop + nvidia-smi or radeontop |
| 7-Zip | p7zip |
| Moo0 Voice Recorder | Audacity / sox |
| Snipping Tool | Flameshot / gnome-screenshot |
| Paint.NET / 美图秀秀 | GIMP / Krita |
| Windows Terminal | Kitty / Alacritty / GNOME Terminal |
| Clipchamp / 剪映 | KDEnlive / OpenShot / DaVinci Resolve |
| Power Automate | Bash scripts / systemd timers |
| Streamlabs / 直播伴侣 | OBS Studio |

### Category C: No Linux Equivalent (Hard Blockers)

| App | Issue |
|-----|-------|
| iGameCenter / GIGABYTE Control Center | Motherboard control (RGB, fan curves, overclock) |
| Realtek Audio Control | Vendor-specific audio driver GUI |
| LDPlayer / 雷电模拟器 | Android emulator — Waydroid is partial replacement |
| BitBrowser / 比特浏览器 | Fingerprint browser |
| WeGame / 三角洲行动 | Chinese game platforms with anti-cheat |
| CC Switch | ReClaude provider manager — Windows-only |
| 企业微信 | No Linux client, Wine unstable |
| 酷狗音乐 | No Linux client, web player |
| 美图秀秀 | No Linux client |

### Category D: Cross-Platform Dev Tools

Works identically on both: Frida, angr, capstone, unicorn, keystone, Ghidra, IDA Pro, Burp Suite, ripgrep, jq.

## Analyzing .lnk Shortcuts & NSIS Installers

When the user has a suspicious `.lnk` / `.exe` on the Desktop (common: repackaged "便携版" tools for AI CLIs, pentest helpers, etc.), dissect before running:

**1. Read the shortcut target (COM):**
```bash
powershell -NoProfile -Command "
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
\$sh = New-Object -ComObject WScript.Shell
\$lnk = \$sh.CreateShortcut('C:\Users\<user>\Desktop\<name>.lnk')
Write-Output ('TargetPath: ' + \$lnk.TargetPath)
Write-Output ('WorkingDirectory: ' + \$lnk.WorkingDirectory)
Write-Output ('IconLocation: ' + \$lnk.IconLocation)
Write-Output ('Description: ' + \$lnk.Description)
Write-Output ('Arguments: ' + \$lnk.Arguments)
"
```
Watch for: `AppData\Local\<name>\` targets (installed, not portable), description lines with author watermarks, and Arguments that could hide flags.

**2. Parse the LNK binary header flags (Python struct):**
```python
data = open(r'<path>.lnk', 'rb').read()
flags = struct.unpack('<I', data[20:24])[0]
print(f'HasTargetIDList={bool(flags&1)} HasLinkInfo={bool(flags&2)} '
      f'HasArguments={bool(flags&0x20)} IsUnicode={bool(flags&0x80)}')
```

**3. Identify the installer type:**
```bash
file "<target>.exe"
# "Nullsoft Installer self-extracting archive" → NSIS bundle
# "Inno Setup" / "InstallShield" → other installer types
```

**4. Inspect the installed layout:**
```bash
ls -la "/c/Users/<user>/AppData/Local/<name>/"
# Look for: INSTALL_LAYOUT.txt, portable_py\ (bundled Python), 
# uninstaller exe, and the actual project directory
```

**5. Security red flags to report:**
- Unsigned NSIS bundle + bundled portable Python = repackaged project (may differ from upstream GitHub source — diff `proxy_relay.py`/`bridge.md` etc. against the official repo)
- `.nerv-transaction-*` / state dirs written at install time = the bundle runs code during install
- Local proxy/MITM capability (listens on 127.0.0.1:port, claims to intercept API traffic) = full man-in-the-middle over your AI CLI traffic; treat as untrusted unless source-verified
- `INSTALL_LAYOUT.txt` + `VERSION` files confirm which upstream project/version the bundle was built from

## Quick Full Scan Command

```bash
winget list > ~/Desktop/software-winget.txt
powershell "Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { \$_.DisplayName } | Select-Object DisplayName, DisplayVersion | Format-Table -AutoSize" > ~/Desktop/software-registry.txt
ls "C:/ProgramData/Microsoft/Windows/Start Menu/Programs/" > ~/Desktop/software-startmenu.txt
```

## Pitfalls

- **MSIX/appx packages** — registry and winget show cryptic IDs. Check start menu for real names.
- **Portable apps** — not registered anywhere. Only in start menu or must be manually searched.
- **Game anti-cheat** — kernel-level anti-cheat (Vanguard, BattlEye, ACE, TenProtect) does NOT work on Linux even through Proton. This is the #1 gaming blocker.
- **NVIDIA drivers** — the control panel is Windows-only. On Linux use `nvidia-settings`.
- **Do NOT claim Linux build exists without checking.** Always verify the developer offers Linux builds before telling the user a tool works on Linux.
