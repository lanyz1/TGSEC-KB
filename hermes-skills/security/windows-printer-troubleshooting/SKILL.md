---
name: windows-printer-troubleshooting
description: >-
  测绘引擎·Use when Windows printer stops mid-print or queue is stuck.
owned: true
tier: general
pack: survey-skill
---

# windows-printer-troubleshooting（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-printer-troubleshooting/`

溯源（仅标记）：`hermes/software-development`

---

# Windows Printer Troubleshooting

One-shot state snapshot: `scripts/print-status.ps1` (printers + jobs + proxy processes + USB selective suspend + HP USB nodes).

## When to Use
- Printer stops after 1-2 pages, prints partial pages, or shows 打印完成 while pages are missing.
- Print queue stuck with "Error, Printing, Retained" jobs, or printer status shows Error.
- Print jobs "complete" on the PC but nothing (or half a page) comes out — especially old HP Deskjets on Windows 10/11.

Symptoms: prints 1-2 pages then stops; "打印完成" but pages missing; test page stalls at half page; job stuck as "Error, Printing, Retained"; printer status Error.

## Golden rule: isolate engine vs data path FIRST
Printer's own self-test page (bypasses the PC entirely):
- HP Deskjet: **unplug USB**, hold the **Resume** button (green triangle), tap **Power** once, release Resume → self-test page prints.
- Self-test FULL → print engine healthy (feed/carriage/ink OK) → problem is PC→printer: **driver / USB / spooler**.
- Self-test also fails → hardware (paper jam, carriage stuck, ink cartridge contact, waste ink pad counter full).
- **"Works fine on another computer" → hardware 100% exonerated** — problem is host-side (driver / USB port / proxy / system components). Stop touching the printer and fix the PC side.

## Diagnostic ladder (run each rung, report result, verify before moving on)
1. **State check** (read-only):
   - `powershell -NoProfile -Command "Get-Printer | Format-List Name,DriverName,PortName,PrinterStatus,WorkOffline"`
   - `powershell -NoProfile -Command "Get-PrintJob -PrinterName '<name>' | Format-List DocumentName,JobStatus,TotalPages,PagesPrinted"`
   - ⚠️ `Get-PrintJob` **requires `-PrinterName`** — a bare call dies with `AmbiguousParameterSet`.
2. **Clear stuck queue + restart spooler** — a retained error job BLOCKS every job behind it:
   ```
   powershell -NoProfile -Command "Stop-Service spooler -Force; Remove-Item 'C:/Windows/System32/spool/PRINTERS/*' -Force; Start-Service spooler"
   ```
   ⚠️ Spooler restart ALONE does not clear retained jobs — they re-enumerate from the spool files. Must delete `PRINTERS\*` while stopped.
3. **Windows test page** (after spooler reset): `rundll32 printui.dll,PrintUIEntry /k /n "<printer name>"`. Smallest possible job; if it stalls → not a document problem.
4. **Driver check**: `Get-Printer -Name <name> | select DriverName`. **`Microsoft IPP Class Driver` on an old HP printer is the #1 suspect** for partial prints / silent job drops / jobs that "complete" without output.
5. **USB selective suspend** (classic mid-print data cut; found ENABLED in a real case):
   ```
   powercfg /query SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226
   powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
   powercfg /setdcvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
   powercfg /setactive SCHEME_CURRENT
   ```
6. **USB re-enumeration** (resets PC-side link only; does NOT reset printer firmware):
   - Find node: `powershell "Get-PnpDevice | Where-Object { $_.InstanceId -like '*03F0*' } | fl FriendlyName,InstanceId,Status"` (03F0 = HP VID; disable the **USB Composite Device** node)
   - `pnputil /disable-device "<InstanceId>"` → sleep 3 → `pnputil /enable-device "<InstanceId>"` → sleep 5 → re-check Status.
7. **Physical power cycle** — the ONLY thing that resets the printer's own USB firmware (a wedged printer ignores all software resets): unplug power AND USB, wait 30s, replug. Explicitly insist the user do this; don't assume it happened.
8. **HP light patterns**: power light fast-blink = paper jam / carriage stuck; slow-blink = ink path; power+ink alternating = cartridge not seated. Blinking power light = the printer's firmware asserts an error — a driver cannot cause that light.

## HP-specific (DeskJet 4900 era, 2026 verified)
- **HP Print and Scan Doctor (HPPSdr)** = official one-click repair (auto-detects printer → reinstalls the proper HP driver):
  - Correct URL: `https://support.hp.com/cn-zh/topic/hp-print-scan-doctor` — the `/help/hp-print-scan-doctor` and `/document/c05061199` variants 404/blank. Page is an Angular SPA; the download button's URL is JS-protected (not extractable via curl or headless-Chrome DOM dump).
  - **Download-name pitfall**: `sp######.exe` (~180MB, "HP Support Assistant" per VersionInfo.FileDescription) is the WRONG tool; the fixer is `HPPSdr.exe` (~12MB — measured 11.9MB in Downloads, 2026-08). Verify with `(Get-Item <file>).VersionInfo | fl FileDescription,ProductName` before launching.
- Windows Update Catalog has NO driver for Deskjet 4900 (`catalog.update.microsoft.com` search returns 0 rows; Device Manager auto-search finds nothing).
- Win11 DriverStore DOES contain `hp_dj_2800_4900.inf_amd64_*` — but it's only a PSA **stub** INF (SoftwareName `HPPSA_HPDeskJet_2800_4900_2502.2.1.0`), not a usable full driver. Don't try to pnputil-install it as the real driver.
- Classic failure signature: prints fine for a few pages → then breaks; Windows jobs show "Error, Retained" at 0 pages while the printer's own self-test is perfect → driver/USB data path, not the engine.

## Proxy software (v2rayN) vs IPP driver — the sneaky one (2026-08 verified)

The **Microsoft IPP Class Driver speaks HTTP internally**; v2rayN (TUN/system proxy, normally always running on this PC for 防封) hijacks those requests → jobs hang `Printing, Retained` at 0 pages, partial prints, blank pages. Verified: user closed v2rayN → test page printed normally; reopened → jobs stuck again. **Whenever a print job is stuck, check proxy processes FIRST** (`Get-Process | ? Name -match 'v2ray|xray|sing-box|clash'`) and have the user close v2rayN temporarily to print (they do it themselves; don't force, but flag it). `netsh winhttp show proxy` can read "Direct access" while v2rayN still interferes (interception is at TUN/route level, not WinHTTP). A stuck job may ALSO persist with v2rayN off — that's a separate IPP-stack problem, not a contradiction. See also `v2rayn-proxy-diagnostics`.

## Blank page (paper out, nothing on it)

Paper emerges cleanly = data path OK, ink failed. Cartridge ink check: pull the cartridge, press a paper towel on the outlet sponge — ink stain = clogged head (HPPSdr printhead clean, or soak cartridge bottom 2-3mm in warm water 5 min); dry = cartridge empty (replace; DeskJet 4900 takes HP 901 black). CAVEAT: a blank page can ALSO be proxy-corrupted data — retest with the proxy off before condemning the ink.

## Silent .docx printing from CLI (WPS/Word COM)

- COM ProgIDs can live in **HKCU only** (WPS): check `Test-Path 'HKCU:\SOFTWARE\Classes\Word.Application'` — an HKLM-only check wrongly reports NO.
- `New-Object -ComObject Word.Application`; `Documents.Open($path,$false,$true)`; `PrintOut()`; `Close(0)`; `Quit()`. Wrap `Open` in a retry loop (first open can return null under WPS).
- Chinese paths: run the PS script via `-EncodedCommand` (UTF-16LE base64) to dodge bash/GBK corruption; Python subprocess stdout → decode with `errors='replace'`.
- Submit jobs one at a time and watch the queue between submissions; don't bulk-submit six docs into a flaky path.

## User-preference rules (this user)
- **Don't grind on download-link/web automation**: after 2-3 failed extraction attempts (404s, JS-protected buttons, SPA pages), STOP hunting programmatically and give the user a manual click-path with the exact URL, the button to click, and what the correct file should be named. This user will find the file themselves if told precisely what to look for; prolonged automated hunting visibly frustrates them.
- Report each diagnostic rung's result as you go; user verifies physical steps (lights, paper, power cycle) and reports back. Ask what the printer's lights are doing — that's the fastest error-code source.

## Verification after a fix
`Get-Printer` → PrinterStatus Normal; print a test page; job should complete with PagesPrinted = TotalPages; confirm physical paper output with the user.

## Pitfalls
- bash on Windows: native curl cannot write to `/tmp` (MSYS) — use `$LOCALAPPDATA/Temp` for scratch files.
- GBK-mojibake in Chinese document names under git-bash is cosmetic; decode contextually (e.g. 01_培训合同, 05_服务交接确认单).
- `Microsoft-Windows-PrintService/Operational` event log is often disabled/empty — don't rely on it; the spooler + physical lights carry the signal.
- `Remove-Item` on spool files and `pnputil` device changes get flagged for approval — that's expected, keep commands explicit and report each step.
- `powercfg /query` on the USB GUID shows `Possible Setting Index: 000/001`; the value that matters is `Current AC/DC Power Setting Index` — 1 = suspend allowed (bad for printers), 0 = disabled (good).
- First job after any reset often errors while the second succeeds — retry once before concluding failure.
- Deleting + re-adding the printer instance (`Remove-Printer` + `Add-Printer` on USB001) does NOT fix a broken driver path — tested 2026-08, test page still Error.
- `pnputil /scan-devices` does not always auto re-add a USB printer after Remove-Printer — re-add manually with `Add-Printer -Name X -DriverName '<driver>' -PortName 'USB001'`.
- `pnputil /disable-device` can fail with "not supported on this OS product" on some device classes — fall back to PowerShell `Disable-PnpDevice` / `Enable-PnpDevice`.
