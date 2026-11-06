# print-status.ps1 — one-shot Windows printer state snapshot.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File print-status.ps1
# Outputs: printers, jobs, proxy processes (IPP-driver killers), USB selective suspend state.
$ErrorActionPreference = 'Continue'

"=== PRINTERS ==="
Get-Printer | Format-List Name, DriverName, PortName, PrinterStatus, WorkOffline

"=== PRINT JOBS (per printer) ==="
Get-Printer | ForEach-Object {
    $p = $_.Name
    Get-PrintJob -PrinterName $p -ErrorAction SilentlyContinue |
        Format-List PrinterName, DocumentName, JobStatus, TotalPages, PagesPrinted
}

"=== PROXY PROCESSES (v2rayN/xray/sing-box can block IPP-driver printing) ==="
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'v2ray|xray|sing-box|clash|mihomo' } |
    Format-List Name, Id

"=== USB SELECTIVE SUSPEND (Current AC/DC index 1 = USB may sleep mid-print) ==="
powercfg /query SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226

"=== HP USB DEVICE NODES (VID 03F0; Status != OK = enumeration problem) ==="
Get-PnpDevice -ErrorAction SilentlyContinue |
    Where-Object { $_.InstanceId -like '*03F0*' } |
    Format-List FriendlyName, InstanceId, Status
