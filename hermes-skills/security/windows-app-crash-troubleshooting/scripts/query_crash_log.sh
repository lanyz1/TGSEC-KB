#!/usr/bin/env bash
# Crash forensics query for Windows apps.
# Usage: ./query_crash_log.sh <AppNameRegex> [Days]     (defaults: Telegram, 7)
#   e.g. ./query_crash_log.sh Telegram 7
# Prints Event Log Id 1000 (Application Error) rows + WER ReportArchive listing.
APP="${1:-Telegram}"
DAYS="${2:-7}"

powershell.exe -NoProfile -Command "
\$app = '$APP'
\$days = $DAYS
\$ev = Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001; StartTime=(Get-Date).AddDays(-\$days)} -ErrorAction SilentlyContinue |
      Where-Object { \$_.Message -match \$app }
Write-Host ('=== Crashes found: ' + \$ev.Count + ' (last ' + \$days + ' days) ===')
\$ev | ForEach-Object {
  \$m = \$_.Message
  \$code = if (\$m -match 'Exception code: (0x[0-9a-fA-F]+)')  { \$matches[1] } else { '-' }
  \$off  = if (\$m -match 'Fault offset: (0x[0-9a-fA-F]+)')     { \$matches[1] } else { '-' }
  \$mod  = if (\$m -match 'Faulting module name: (\S+)')        { \$matches[1] } else { '-' }
  \$path = if (\$m -match 'Faulting application path: (\S+)')   { \$matches[1] } else { '-' }
  Write-Host (\$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss') + '  code=' + \$code + '  offset=' + \$off + '  module=' + \$mod)
  Write-Host ('    ' + \$path)
}
"
echo "=== WER ReportArchive (most recent 5) ==="
ls -t "C:/ProgramData/Microsoft/Windows/WER/ReportArchive/" 2>/dev/null | grep -i "$APP" | head -5
echo "=== Recycle Bin has app data? (quick check) ==="
powershell.exe -NoProfile -Command "Get-ChildItem -Path 'C:\\\$RECYCLE.BIN','D:\\\$RECYCLE.BIN' -Recurse -ErrorAction SilentlyContinue | Where-Object {\$_.Name -match '$APP'} | Select-Object -First 5 FullName"
echo "(empty = nothing recoverable from Recycle Bin; try 'vssadmin list shadows' for VSS)"
