# Telegram Desktop crash case (2026-07-31)

## Symptom
Telegram Desktop 7.0.6 (auto-updated 2026-07-27) crashes when opening specific chats.
User report: "刚打开不崩，用了一下又崩了" (opens fine, crashes after use / on specific chats).

## Evidence trail
- Event Log Id 1000 (Application Error): exception `0xc0000409` (STATUS_STACK_BUFFER_OVERRUN, BEX64),
  faulting module = `Telegram.exe` itself, **identical fault offset `0x0000000005a3c475` across all 3 crashes**.
- WER bucket Id 1001: `BEX64`, `Report.wer` UTF-16 (read via PowerShell `Get-Content`, not cat).
- Loaded modules: only Telegram.exe + system DLLs → no third-party injection.
- Vendor log `D:\Telegram Desktop\log.txt`: OpenGL/ANGLE init OK (NVIDIA RTX 5080 D3D11),
  then repeated `History::unknownMessageDeleted` for Peer 3931449353 → resync markers, not fatal.
- Environment: v2rayN + xray + sing-box all running; ToDesk/向日葵(Oray)/GameViewer virtual display
  adapters + NVIDIA RTX 5080 + AMD iGPU. Windows 10 (build 26200.8655). Disk 168G free, RAM 25.8G free.

## Verdict path
1. Cache reset (rename `tdata/user_data` + `user_data#2`, keep auth) → still crashed, same offset
   → NOT cache corruption.
2. Identical offset + post-update onset → deterministic 7.0.6 version bug.
3. GitHub releases: 7.0.6 was latest, no fix → rollback to 7.0.5
   (`tsetup-x64.7.0.5.exe`, 54MB, via `curl -x http://127.0.0.1:10808 -L`).

## Telegram Desktop facts (durable)
- **Chat messages live in the cloud; local `tdata` is cache + auth.** Re-login restores all chats.
- `tdata/` layout: `user_data/` (chat history db, ~1GB), `user_data#2/` (2nd account), `key_datas`
  (auth keys), `settingss`, `log.txt` (vendor log), `dumps/` (crash dumps — empty here).
- GitHub releases: `telegramdesktop/tdesktop`, assets `tsetup-x64.<ver>.exe` (installer),
  `tportable-x64.<ver>.zip` (portable).

## The uninstall disaster (the real lesson)
Silent uninstall: `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
- **Deleted the ENTIRE `D:\Telegram Desktop\` dir including `tdata` AND the `user_data.bak.*`
  backups that had been renamed inside it.** Nothing in Recycle Bin; `vssadmin list shadows` = empty.
- Impact: login state lost (re-login needed); chat history safe (cloud); local media cache lost (re-downloads).
- **Rule: copy user data OUTSIDE the install dir before any uninstall. Rename-in-place is not a backup.**

## Install path pitfall
`Start-Process ... -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR=D:\Telegram Desktop' -Wait`
→ installed to `D:\Telegram` (truncated at the space). Fix: `'/DIR="D:\Telegram Desktop"'` (embedded quotes).
Verify with `(Get-Item '...Telegram.exe').VersionInfo` — exit code alone said success.

## Final state
7.0.5 installed at `D:\Telegram` (not the old `D:\Telegram Desktop`); user must re-login (SMS code).
Crash fix confirmed: rollback removed the 0xc0000409 fault.
