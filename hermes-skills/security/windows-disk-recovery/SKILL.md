---
name: windows-disk-recovery
description: >-
  测绘引擎·Windows disk space analysis, identifying space hogs, safely moving data between
  drives, AppData symlink relocation, and cache cleanup. Systematic approach for when the
  user's C: drive is nearly full.
owned: true
tier: general
pack: survey-skill
---

# windows-disk-recovery（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-disk-recovery/`

溯源（仅标记）：`hermes/software-development`

---

# Windows Disk Recovery

## Overview

Systematic approach to reclaiming disk space on Windows when C: is full but other drives (D:, E:) have plenty of room. Never assume — always measure first, then act.

## Phase 1: Measure

### Step 0 — System files first (instant, no recursion)

git-bash `ls -la /c/` shows root-level file sizes immediately — pagefile.sys, hiberfil.sys, swapfile.sys are often 10-40GB combined and need NO scan:

```bash
ls -la /c/ | grep -v '^d'
```

- **hiberfil.sys** ≈ 70-80% of RAM (26GB on a 32GB box). `powercfg /h off` deletes it instantly — that's 20-35GB. Side effect: Fast Startup is disabled too. NOTE: hiberfil.sys CANNOT be relocated to another drive — Windows requires it at the C: root, so "迁移休眠文件" is not possible; only on/off.
- **pagefile.sys** CAN be relocated to D: via registry (see Tier 5) — frees the file on reboot.

### Step 1 — Drive-level overview

```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Size(GB)';E={[math]::Round($_.Used/1GB,1)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}}
```

### Step 2 — Find the biggest folders

Common space hogs on C::

| Directory | Typical Cause |
|-----------|--------------|
| `%USERPROFILE%\\Downloads` | Large zip files, installers, downloaded archives |
| `%USERPROFILE%\\Documents` | App data files (WeChat, QQ, WXWork store files here) |
| `%USERPROFILE%\\AppData\\Roaming` | App caches (Tencent, SodaMusic, BitBrowser, KuGou) |
| `%USERPROFILE%\\AppData\\Local` | Hermes data, npm/pnpm/uv cache, temp files |
| `C:\\Windows\\Temp` | System temporary files |

Drill into each:

**CRITICAL: git-bash `du` is unusably slow on NTFS** — full-profile scans time out at 300s+. Do NOT hand-run `du -sh` over large trees (single dirs like Downloads are fine; userprofile/Documents/AppData are not). Instead launch the bundled background scanner (scripts/scan_c_drive.ps1) which uses .NET enumeration and writes a report to `Desktop\c_drive_scan.txt`:

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<skill_dir>/scripts/scan_c_drive.ps1"   # run with terminal(background=true, notify_on_complete=true)
```

It scans C:\ top level + user profile + AppData Local/Roaming + Documents + Downloads + Program Files (+x86) + ProgramData, listing dirs > 200MB (~6 min). Read results with `read_file ~/Desktop/c_drive_scan.txt`.

Pitfall when reading the report: `C:\Users\<user>\Application Data` (junction → AppData\Roaming) and `C:\Users\<user>\My Documents` (junction → Documents) appear as separate top-level entries with the SAME data — dedupe them, don't double-count.

### Step 3 — Download folder analysis

```powershell
$dl = "$env:USERPROFILE\\Downloads"
Get-ChildItem $dl -File | Group-Object { [System.IO.Path]::GetExtension($_.Name).ToLower() } | Sort-Object Count -Descending | Select-Object @{N='Ext';E={$_.Name}}, Count, @{N='SizeGB';E={[math]::Round((($_.Group | Measure-Object -Property Length -Sum).Sum)/1GB,2)}}
```

## Phase 2: Categorize and Act

### Tier 1 — Safe to Delete (caches, temp files)

| Target | Command |
|--------|---------|
| npm cache | `npm cache clean --force` |
| pnpm cache | `pnpm store prune` |
| pip cache | `pip cache purge` |
| uv cache | `uv cache clean` |
| Temp files | `rm -rf /c/Users/Administrator/AppData/Local/Temp/*` |
| Crash dumps | `rm -rf /c/Users/Administrator/AppData/Local/CrashDumps/*` |

### Tier 2 — Move Large Downloads to D:/E:

```bash
mkdir -p /d/installers
mv /c/Users/Administrator/Downloads/*.exe /d/installers/
mv /c/Users/Administrator/Downloads/*.msi /d/installers/
mv /c/Users/Administrator/Downloads/*.zip /d/archives/
```

### Tier 3 — Move WeChat/WXWork Data

WeChat stores files in `Documents/xwechat_files/` — often 20+ GB.
1. Close WeChat
2. WeChat Settings -> File Management -> Change path to `D:\WeChatFiles`
3. Manually move old folder

Same for WXWork in `Documents/WXWork/`.

Additional Tencent cache (safe to delete, after closing WeChat/WXWork — total 5-8GB):
- `AppData\Roaming\Tencent\xwechat\{radium, log, update, XPlugin}` — renderer cache, logs, old updaters
- `AppData\Roaming\Tencent\WXWork\{upgrade, cef, wmpf_Applet, Log}` — old upgrade installers + cache

### Tier 4 — Symlink (Junction) Relocation

For apps that hardcode their data path, move the folder to D: (robocopy for big dirs — see Tier 5), then junction. **Do NOT use `cmd //c mklink` from git-bash — MSYS path conversion mangles `C:\...` args and mklink fails silently (looks like nothing happened).** Use PowerShell:

```bash
# Move folder to D: (exit 0-7 = success; 1 = files copied)
robocopy 'C:\Users\Administrator\AppData\Local\hermes' 'D:\hermes-data' /E /MOVE /MT:16 /R:1 /W:1 /NFL /NDL /NP

# Create junction — works from git-bash, no path mangling
powershell.exe -NoProfile -Command "New-Item -ItemType Junction -Path 'C:\Users\Administrator\AppData\Local\hermes' -Target 'D:\hermes-data'"

# Verify
powershell.exe -NoProfile -Command "(Get-Item 'C:\Users\Administrator\AppData\Local\hermes').LinkType; (Get-Item 'C:\Users\Administrator\AppData\Local\hermes').Target"
# → prints: Junction / D:\hermes-data
```

Common candidates:

| App Data Path | Size Range | Notes |
|--------------|-----------|-------|
| `AppData\Local\hermes` | 2-5 GB | Hermes agent session data |
| `AppData\Local\Docker\wsl` | 10-80 GB | Docker WSL vhdx — see Tier 5, often the #1 hog |
| `AppData\Roaming\SodaMusic` | 3-5 GB | 汽水音乐 cache (LunaCacheV2) |
| `AppData\Roaming\webcast_mate` | ~1 GB | 直播伴侣 cache |
| `AppData\Roaming\douyin` | 0.8-1 GB | 抖音 cache |
| `AppData\Local\JianyingPro` | 0.7 GB | 剪映 resources |
| `AppData\Roaming\KuGou8` | 0.5 GB | 酷狗音乐 cache |

## Tier 5 — Docker WSL vhdx & pagefile relocation

### Docker (often the #1 single hog, 40-80GB)

Everything lives in `%LOCALAPPDATA%\Docker\wsl\` — `disk\docker_data.vhdx` (images/containers/volumes) is the big one; `main\ext4.vhdx` is small.

1. **Inspect**: start Docker Desktop, `docker system df` → reclaimable per type (Images/Containers/Volumes/Build Cache). `docker images` EXTRA column `U` = image not used by any container. Build cache (`docker builder prune -f`) is always safe; `docker image prune -a` deletes ALL unused images — check for the user's sandbox images first (kali-linux, strix-sandbox, vxcontrol stacks) and get permission before nuking.
2. **Compact vhdx (lossless — only reclaims slack, NOT real data)**: `wsl --shutdown`, then diskpart:
   ```
   select vdisk file="C:\Users\Administrator\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
   attach vdisk readonly
   compact vdisk
   detach vdisk
   ```
   If the disk holds real data expect little gain (47GB → 44GB in practice). Don't promise big numbers.
3. **Full migration to D:**: quit Docker Desktop (taskkill), `wsl --shutdown`, robocopy /MOVE the whole `wsl` dir to `D:\DockerData\wsl`, junction it back (Tier 4), restart Docker Desktop, verify `docker images` still lists everything before declaring success.

### pagefile.sys relocation (frees 8-16GB after reboot)

```bash
powershell.exe -NoProfile -Command "Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name AutomaticManagedPagefile -Value 0 -Type DWord; Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name PagingFiles -Value @('D:\pagefile.sys 0') -Type MultiString"
```

Reboot required — Windows then deletes C:\pagefile.sys and creates D:\pagefile.sys (0 = system-managed size on D:). Old C:\pagefile.sys can be deleted manually after reboot. hiberfil.sys has NO relocation option — only `powercfg /h off` (delete) or `/h on` (recreate on C:).

## Maximum Impact Estimate

| Operation | Expected Free Space |
|-----------|-------------------|
| Clear package caches (npm/pnpm/pip/uv) | ~3-5 GB |
| Clear Temp + CrashDumps + Recycle Bin | ~3-5 GB |
| Disable hibernation (`powercfg /h off`) | 20-35 GB (70-80% of RAM) |
| Relocate pagefile to D: | 8-16 GB (after reboot) |
| Move large downloads | 10-80+ GB |
| WeChat/WXWork relocation | 15-30 GB |
| Clear Tencent/SodaMusic caches | 5-12 GB |
| Docker vhdx compact / migrate to D: | 5-60 GB |
| AppData symlink relocation | 5-10 GB |
| **Total** | **70-230+ GB** |

## Pitfalls

- **Do NOT delete `%TEMP%` while apps are running** — locked files cause skips. Close Chrome, WeChat, QQ first.
- **Do NOT symlink entire `AppData`** — Windows checks junction targets and some apps break. Symlink individual subdirectories.
- **WeChat must be closed** when moving files. Set new path first, then delete old data.
- **NVIDIA/AMD shader cache** in `AppData\\Local\\NVIDIA` or `AMD` — safe to delete, regenerates on next game launch.
- **`C:\\Windows\\WinSxS`** — do NOT touch manually. Use `DISM /Online /Cleanup-Image /StartComponentCleanup`.
- **Verify junctions** with `dir /al C:\Users\Administrator\AppData\Local\` — look for `<JUNCTION>` tag (or PowerShell `(Get-Item <path>).LinkType` → `Junction`).
- **Junction points survive reboots** but do NOT survive drive letter changes.
- **robocopy exit codes**: 0-7 = success (1 = files copied; 3 = files copied + extras in dest). Treat 8+ as failure. /MOVE deletes source; rerunning resumes cleanly, so a chained script is safe.
- **Cross-drive `mv` in git-bash is a copy+delete** — for 20-50GB dirs use `robocopy /MOVE /MT:16` in background with notify_on_complete instead of `mv` (which gives no progress and blocks the turn).
- **`docker image prune -a` can destroy the user's pentest sandbox images** (vxcontrol/kali-linux, strix-sandbox) — they show as "unused" when containers are stopped. Always show `docker images` (U column) and confirm before pruning.
- **SodaMusic**: `AppData\Roaming\SodaMusic\LunaCacheV2` is the 3-5GB song cache — kill SodaMusic.exe processes (often many PIDs) before deleting.
- **Recycle Bin**: `powershell.exe -NoProfile -Command "Clear-RecycleBin -Force"` — faster than scanning `$Recycle.Bin` with du.
