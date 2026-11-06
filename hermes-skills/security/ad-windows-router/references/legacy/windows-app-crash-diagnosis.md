<!-- archived from /root/.hermes/skills/security/windows-app-crash-diagnosis/SKILL.md on 2026-10-21 -->

---
name: windows-app-crash-diagnosis
description: >-
  测绘引擎·Use when a Windows desktop app keeps crashing/闪退.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/windows-app-crash-diagnosis`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/windows-app-crash-diagnosis/…')`，不要相对 `references/legacy/` 解析。

# windows-app-crash-diagnosis（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-app-crash-diagnosis/`

溯源（仅标记）：`hermes/software-development`

---

# Windows App Crash Diagnosis (闪退排查)

User reports "XXX 一直闪退" (app crashes repeatedly). Do NOT guess — collect evidence first, then classify the crash, then fix with rollback safety.

## Phase 1 — Evidence (parallel, ~1 min)

### 1. Windows Event Log (crash records)

```bash
powershell.exe -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001,1002; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 50 -ErrorAction SilentlyContinue | Where-Object {\$_.Message -match 'Telegram'} | Select-Object -First 10 | Format-List TimeCreated, Id, ProviderName, Message"
```

- Swap the match string for the real app name.
- Id 1000 = Application Error (the crash itself), 1001 = WER bucket, 1002 = hang.
- The Message contains the gold: exception code, faulting module, install path, version, timestamp, process id.
- Count records + list timestamps to see frequency (2 crashes in 1 min = ongoing; 2 in 7 days = maybe one-off).

### 2. WER ReportArchive (optional detail)

`C:/ProgramData/Microsoft/Windows/WER/ReportArchive/AppCrash_<App>_*/Report.wer` — UTF-16LE, cat shows garbage; the Event Log message already carries the key fields (P1–P9), so prefer Get-WinEvent.

### 3. Rule out resources

```bash
df -h /c | tail -1                      # disk free
powershell.exe -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select-Object @{n='FreeGB';e={[math]::Round(\$_.FreePhysicalMemory/1MB,1)}}, @{n='TotalGB';e={[math]::Round(\$_.TotalVisibleMemorySize/1MB,1)}}"
```

### 4. App's own logs

Check the install dir for `log.txt` / logs folder — often has the last actions before the crash (e.g. Telegram: `History::unknownMessageDeleted Peer ID: ...` = local history sync problems with a specific chat).

### 5. Conflict software inventory

```bash
tasklist 2>/dev/null | grep -iE "clash|v2ray|xray|sing-box|ssr|shadowsocks|netch|hiddify|nekobox|trojan|verge|mihomo"
powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion"
```

Multiple proxies (v2rayN + xray + sing-box together) and multiple remote-desktop virtual GPUs (Todesk/向日葵/GameViewer) are common on this user's machines and cause network/renderer conflicts.

## Phase 2 — Classify the crash

| Signature | Meaning |
|---|---|
| `0xc0000409` + BEX64 | STATUS_STACK_BUFFER_OVERRUN — often the app's own __fastfail/assert. Faulting module = app itself, loaded modules only app + system DLLs → NOT DLL injection, NOT 输入法/杀软劫持 |
| Crash right after auto-update | New-version incompatibility with old local cache — check exe timestamp vs install dir date (`ls -la --time-style=long-iso`) |
| Crash on specific action (open a chat/doc) | Local cache DB corrupted (read of a bad record) |
| Crash only at startup | Often corrupted cache too, or GPU/ANGLE renderer (check log.txt OpenGL lines) |

## Phase 3 — Fix (cache rebuild, rollback-safe)

Pattern: **backup by RENAME, never delete** → restart → app rebuilds from server; login preserved if credentials live outside the data dir.

For Telegram Desktop (see references/telegram-desktop-tdata.md for full case):

```bash
taskkill //F //IM Telegram.exe 2>/dev/null   # fallback: powershell Stop-Process -Name Telegram
cd "D:/Telegram Desktop/tdata"
mv user_data user_data.bak.$(date +%Y%m%d_%H%M)      # 1.1G history DB
mv user_data#2 user_data#2.bak.$(date +%Y%m%d_%H%M)  # second account, if present
powershell.exe -NoProfile -Command "Start-Process -FilePath 'D:\Telegram Desktop\Telegram.exe'"
sleep 15 && tasklist 2>/dev/null | grep -i telegram   # process alive = good
tail -5 "D:/Telegram Desktop/log.txt"                 # should show re-sync
```

Verify BEFORE declaring success: process alive after 10–15s (a crash happens fast), then ask the user to trigger the exact action that crashed before (open that chat).

## Pitfalls

- **`taskkill //F //IM` in git-bash MSYS can error** "Invalid argument/option - '//F'". Use `taskkill //F //PID <pid>` or PowerShell `Stop-Process -Name <app>`.
- **`cmd //c start "" "path"` can hang the bash terminal** — use `powershell.exe -NoProfile -Command "Start-Process -FilePath '...'"` to launch GUI apps.
- Process may already be dead → taskkill fails; check `tasklist | grep -i <app>` and treat "already exited" as success.
- Backup dirs are 1GB+ — renaming (same volume, instant) beats copying; keep them until the user confirms fixed, then offer cleanup.
- Tell the user the fix is verified by RE-TRIGGERING the crashing action, not just by launch success.

## References

- `references/telegram-desktop-tdata.md` — full Telegram Desktop 0xc0000409 case: tdata layout, evidence chain, fix + verification.
