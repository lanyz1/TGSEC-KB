# Background C: drive scanner — fast .NET enumeration, writes report to Desktop\c_drive_scan.txt
# Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scan_c_drive.ps1
# Run with terminal(background=true, notify_on_complete=true) — takes ~6 min on a 250GB drive.
# NOTE: do NOT use git-bash `du` for this — it times out on NTFS (>300s for userprofile alone).
$ErrorActionPreference = 'SilentlyContinue'
$out = Join-Path $env:USERPROFILE 'Desktop\c_drive_scan.txt'
"=== C: drive scan $(Get-Date) ===" | Out-File $out -Encoding utf8

function Get-DirSizeMB([string]$path) {
    if (-not (Test-Path $path)) { return -1 }
    $sum = 0L
    try {
        foreach ($f in [System.IO.Directory]::EnumerateFiles($path, '*', [System.IO.SearchOption]::AllDirectories)) {
            try { $sum += (New-Object System.IO.FileInfo $f).Length } catch {}
        }
    } catch {}
    return [math]::Round($sum/1MB, 1)
}

function Scan-Level([string]$basePath, [string]$label, [double]$minMB = 200) {
    "`n### $label" | Out-File $out -Append -Encoding utf8
    Get-ChildItem -LiteralPath $basePath -Directory -Force | ForEach-Object {
        $mb = Get-DirSizeMB $_.FullName
        if ($mb -gt $minMB) { "{0,10:N1} MB  {1}" -f $mb, $_.FullName | Out-File $out -Append -Encoding utf8 }
    }
}

# C:\ top level (dirs > 500MB)
"`n### C:\ top level" | Out-File $out -Append -Encoding utf8
Get-ChildItem -LiteralPath 'C:\' -Directory -Force | ForEach-Object {
    $mb = Get-DirSizeMB $_.FullName
    if ($mb -gt 500) { "{0,10:N1} MB  {1}" -f $mb, $_.FullName | Out-File $out -Append -Encoding utf8 }
}

# User profile tree (dirs > 200MB)
Scan-Level $env:USERPROFILE "C:\Users\$($env:USERNAME) (top)"
Scan-Level (Join-Path $env:USERPROFILE 'AppData\Local') 'AppData\Local (subdirs)'
Scan-Level (Join-Path $env:USERPROFILE 'AppData\Roaming') 'AppData\Roaming (subdirs)'
Scan-Level (Join-Path $env:USERPROFILE 'Documents') 'Documents (subdirs)'
Scan-Level (Join-Path $env:USERPROFILE 'Downloads') 'Downloads (subdirs)'
Scan-Level 'C:\Program Files' 'Program Files (subdirs)'
Scan-Level 'C:\Program Files (x86)' 'Program Files x86 (subdirs)'
Scan-Level 'C:\ProgramData' 'ProgramData (subdirs)'

"`n=== DONE $(Get-Date) ===" | Out-File $out -Append -Encoding utf8
# Reading the report: watch for double-counted junctions:
#   C:\Users\<user>\Application Data  -> junction to AppData\Roaming (same data)
#   C:\Users\<user>\My Documents      -> junction to Documents (same data)
