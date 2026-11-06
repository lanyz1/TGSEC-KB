## CC-Panes process recovery (won't open / frozen window) — verified Aug 2026

CC-Panes is Tauri 2 + WebView2. Two distinct "broken" symptoms, two different fixes.
Install dir (release): `C:\Users\<user>\AppData\Local\cc-panes\cc-panes.exe`; data in
`~/.cc-panes/` (debug: `~/.cc-panes-dev/`).

### Symptom A — clicking the desktop icon does nothing ("打不开")

The old instance's process is ALIVE but its main window is hidden (`visible=False`);
the new instance exits within seconds via the **single-instance lock**. Don't relaunch
or kill — reveal the hidden window:

```powershell
# Get-Process cc-panes .MainWindowHandle may point at a 16×16 HELPER window
# (titled like "com.ccpanes.app-siw") — not the real one. EnumWindows the cc-panes
# PID and find the window titled "CC-Panes" (it may be fullscreen-sized but invisible).
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W32H {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
$h = [IntPtr]<real window hwnd, e.g. 11670950>
[W32H]::ShowWindow($h, 9)        # SW_RESTORE
[W32H]::ShowWindow($h, 5)        # SW_SHOW
[W32H]::SetForegroundWindow($h)
# verify: IsWindowVisible → True, GetWindowRect → full size
```

### Symptom B — window visible but drag / maximize / clicks dead

Main process `Responding=True`, but two `msedgewebview2` renderer processes each spin
~50% CPU → WebView2 renderer busy-loop; the UI is a static frame. Restart is the only fix:

```powershell
$p = Get-Process cc-panes; $p.CloseMainWindow(); Start-Sleep 3
if (!$p.HasExited) { $p.Kill() }                  # graceful first, force only if stuck
Stop-Process -Name cc-panes-daemon,cc-panes-web -Force   # orphans keep :18080 bound
# relaunch: & "$env:LOCALAPPDATA\cc-panes\cc-panes.exe"
# verify healthy: main CPU ≈0.06s/5s (~1%); no webview2 process >30% after settle;
#   netstat shows 127.0.0.1:18080 LISTENING again
```

### Pitfalls

- **Killing only the main process leaves orphans**: `cc-panes-daemon` + `cc-panes-web`
  survive and keep port 18080 bound; kill all three before relaunching.
- **`taskkill //F //PID` breaks under git-bash** (MSYS mangles `/F`). Use PowerShell
  `Stop-Process` instead.
- **Restart needs user consent**: this user's rule — always ask before
  kill/restart (they were burned by an unsanctioned kill of cc-panes).
- Single-instance lock means "won't open" is usually NOT a crash — check `tasklist |
  grep cc-panes` for a live process BEFORE assuming a corrupt install.

