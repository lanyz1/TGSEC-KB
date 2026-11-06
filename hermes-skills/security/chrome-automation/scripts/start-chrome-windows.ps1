$ErrorActionPreference = "Stop"
$CHROME_AUTOMATION_DIR = if ($env:CHROME_AUTOMATION_DIR) { $env:CHROME_AUTOMATION_DIR } else { "$HOME\AppData\Local\Google\Chrome-SurveyEngine" }
$CHROME_APP = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$DEBUG_PORT = 9222
if (-not (Test-Path $CHROME_APP)) { Write-Host "[!] Chrome not found"; exit 1 }
New-Item -ItemType Directory -Path $CHROME_AUTOMATION_DIR -Force | Out-Null
Write-Host "[ok] empty job profile (will not copy personal Chrome)"
Start-Process -FilePath $CHROME_APP -ArgumentList "--remote-debugging-port=$DEBUG_PORT","--user-data-dir=$CHROME_AUTOMATION_DIR","--no-first-run"
Write-Host "[ok] debug port $DEBUG_PORT"
