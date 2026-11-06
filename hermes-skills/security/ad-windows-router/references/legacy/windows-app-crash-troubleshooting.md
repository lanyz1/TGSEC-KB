<!-- archived from /root/.hermes/skills/security/windows-app-crash-troubleshooting/SKILL.md on 2026-10-21 -->

---
name: windows-app-crash-troubleshooting
description: >-
  测绘引擎·Use when a Windows app闪退/crashes: diagnose and fix.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/windows-app-crash-troubleshooting`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/windows-app-crash-troubleshooting/…')`，不要相对 `references/legacy/` 解析。

# windows-app-crash-troubleshooting（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-app-crash-troubleshooting/`

溯源（仅标记）：`hermes/software-development`

---

# Windows App Crash Troubleshooting

Use when a Windows desktop app crashes / flashes / exits unexpectedly (user says "闪退" / "keeps crashing").

## Diagnosis workflow — evidence first, no guessing

1. **Event Log** — Application Error (Id 1000) + WER bucket (Id 1001), last N days, filtered by app name:
   `scripts/query_crash_log.sh <AppNameRegex> [Days]` does this for you.
   Extract: exception code, fault offset, faulting module, app path + version, crash count + timestamps.
2. **WER ReportArchive** — `C:\ProgramData\Microsoft\Windows\WER\ReportArchive\AppCrash_<App>_*`
   `Report.wer` is **UTF-16 encoded** — `cat` shows NUL garbage; use PowerShell `Get-Content` or iconv.
   Check the `LoadedModule[...]` list for third-party DLL injection (IME, AV, translator hooks).
3. **Vendor log** — app-specific (e.g. `D:\Telegram Desktop\log.txt`); shows last actions before crash and sync anomalies.
4. **Environment conflict scan** — proxy/VPN clients (clash/v2ray/xray/sing-box), virtual display adapters (ToDesk/向日葵/GameViewer remote-desktop GPUs). Many virtual GPUs + multi-proxy setups crash Qt/ANGLE apps. Note this user's box runs **v2rayN+xray+sing-box simultaneously + 3 remote-desktop virtual GPUs** — always scan for these.
5. **Crash frequency + trigger**: isolated 2-3 crashes vs every-use; "opens fine, crashes when opening a specific chat/file".

## Key heuristics

- **Identical fault offset + same exception code across multiple crashes** (esp. `0xc0000409` BEX64) = deterministic app/version bug, NOT cache corruption. A cache reset will NOT fix it.
- `0xc0000409` = STATUS_STACK_BUFFER_OVERRUN, raised via `__fastfail` — usually an app-internal assert, not an exploit.
- Faulting module = the app's own exe + no injected DLLs → app bug or GPU/network environment, not third-party hooks.
- Crash started right after a recent auto-update → **try version rollback before deep forensics** (cheap, often the fix).

## Fix ladder

1. **Cache reset** — rename (never delete) cache dirs; app re-syncs from cloud, login often survives. E.g. Telegram: `tdata/user_data`.
2. **Version rollback** — fetch previous release from vendor GitHub releases (this user: GitHub needs proxy `curl -x http://127.0.0.1:10808 -L`).
3. **Full reinstall** — last resort only.

## CRITICAL PITFALLS (learned the hard way)

1. **Inno Setup silent uninstall (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`) DELETES the ENTIRE install directory** — including user data (auth keys, chat caches) AND any backups you renamed *inside* that directory. Files go straight to disk, **not** Recycle Bin; VSS shadow copies are usually absent (`vssadmin list shadows` = empty).
   → ALWAYS copy user data to a location OUTSIDE the install dir (Desktop, other drive) before uninstalling. **Rename-in-place is NOT a backup.**
2. **Silent install `/DIR` with spaces breaks**: `Start-Process -ArgumentList '/DIR=D:\App Name'` truncates at the space (installed to `D:\App`). Quote the value: `'/DIR="D:\App Name"'` (embedded double quotes).
3. **Verify the install landed** — check registry uninstall key or `(Get-Item ...exe).VersionInfo`, never trust the installer's exit code alone (it returned success while going to the wrong path).
4. **After uninstaller deletes data, verify recoverability before promising anything**: check Recycle Bin + `vssadmin list shadows` first, then tell the user honestly what's lost and what's recoverable (e.g. cloud-synced chats vs local-only state).

## "Won't open" ≠ crashed — single-instance lock + hidden window (check process FIRST)

Symptom: user clicks the desktop shortcut and "nothing happens" / "app won't open".
**Before assuming a crash or reinstalling: check whether the process is already alive.**
Single-instance apps (Tauri, Electron, many tray apps) silently exit a second launch and hand
off to the existing instance — if that instance's main window is hidden (tray-collapse,
zombie WebView, off-screen), the user sees a dead shortcut while the app actually runs.

Diagnosis order:
1. `tasklist | grep -i <app>` — if a process exists, it's alive. Also check daemon/web
   companion processes (cc-panes has `cc-panes-daemon.exe`, `cc-panes-web.exe`, port 18080).
2. `Get-Process <app> | Select MainWindowTitle,Responding,MainWindowHandle` — a
   `MainWindowHandle` pointing at a 16×16 window with an internal title (e.g.
   `com.ccpanes.app-siw`) is a helper window, NOT the main UI. CPU time is a hint: a
   "hidden" app often shows hours of accumulated CPU from a stuck render loop.
3. **Enumerate ALL top-level windows of the PID** — the real titled window (e.g. "CC-Panes")
   may exist but be `visible=False`. PowerShell: `Add-Type` with `user32.dll`
   `EnumWindows` + `GetWindowText` + `GetWindowThreadProcessId` + `IsWindowVisible` +
   `GetWindowRect`, filter by PID, print hwnd/title/visible/rect for each.
4. **Fix — restore the hidden real window** (visible False → True) via `user32.dll`:
   ```powershell
   [W32]::ShowWindow($h, 9)   # SW_RESTORE
   [W32]::ShowWindow($h, 5)   # SW_SHOW
   [W32]::SetWindowPos($h, -1, 0,0,0,0, 0x43)  # HWND_TOPMOST + SWP_SHOWWINDOW
   [W32]::SetForegroundWindow($h)
   ```
5. Screen-grab (`CopyFromScreen` → PNG) + vision-check to confirm the UI actually rendered
   before declaring success — a `Responding=True` process can still have a blank WebView.

Pitfalls:
- `MainWindowHandle` can CHANGE between calls (16×16 helper → real window) — don't cache it;
  re-enumerate per call.
- Never kill the process "to restart it" without user consent (this user was burned by a
  forced cc-panes kill — see memory). The hidden-window restore is the non-destructive fix.
- A fresh launch that exits after a few seconds with boot logs stopping mid-init (e.g. at
  `building tauri app...`) is the single-instance handoff, NOT a startup crash — confirm with
  `tasklist` before debugging a phantom "crash".

## Worked example

`references/telegram-desktop-crash-case.md` — Telegram 7.0.6 crash (0xc0000409), cache reset, rollback to 7.0.5, uninstaller data-loss aftermath, tdata layout, machine fingerprint.

## Support files

- `scripts/query_crash_log.sh` — crash forensics query (Event Log Id 1000 + WER archive listing) for any app name.
- `references/telegram-desktop-crash-case.md` — full worked case.
