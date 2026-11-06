param(
  [Parameter(Mandatory=$true)][string]$Action,
  [int]$X = 0, [int]$Y = 0,
  [string]$Text = "",
  [string]$Shot = "C:\Users\Administrator\AppData\Local\Temp\todesk_shot.png"
)

# ToDesk 远程会话窗口驱动工具（路线 B，无 computer_use 时用）
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File todesk_ctl.ps1 -Action <action> [参数]
#   foreground          置前 ToDesk 窗口（必须先做）
#   click X Y           窗口相对坐标点击（X/Y 相对 ToDesk 窗口左上角）
#   clickabs X Y        屏幕绝对坐标点击
#   type "text"         SendKeys 打字（{}%^+() 为特殊字符，长命令走剪贴板粘贴）
#   key "^{ESC}"        按键（SendKeys 语法）
#   shot                截图当前窗口到 $Shot
#   winrect             打印窗口矩形
# 配合流程: foreground -> 截图 -> vision 分析 -> click/type -> shot 验证
# 剪贴板粘贴: 本机 powershell "Set-Clipboard -Value '<内容>'" 后远程窗口 Ctrl+V

Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class U {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
'@

$p = Get-Process ToDesk -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { Write-Output 'ERR:NO_TODESK_WINDOW'; exit 1 }
$hwnd = $p.MainWindowHandle

function Get-WinRect {
  $r = New-Object U+RECT
  [U]::GetWindowRect($hwnd, [ref]$r) | Out-Null
  return $r
}

function Send-Key([string]$keys) {
  [System.Windows.Forms.SendKeys]::SendWait($keys)
  Start-Sleep -Milliseconds 120
}

function Click-At([int]$cx, [int]$cy) {
  [U]::SetCursorPos($cx, $cy)
  Start-Sleep -Milliseconds 80
  [U]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)  # left down
  Start-Sleep -Milliseconds 40
  [U]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)  # left up
  Start-Sleep -Milliseconds 150
}

function Take-Shot {
  $r = Get-WinRect
  $w = $r.R - $r.L; $h = $r.B - $r.T
  $bmp = New-Object System.Drawing.Bitmap($w, $h)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
  $bmp.Save($Shot, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  Write-Output "SHOT:$Shot ($w x $h) at ($($r.L),$($r.T))"
}

switch ($Action) {
  "foreground" {
    [U]::SetForegroundWindow($hwnd) | Out-Null
    Write-Output "FOREGROUND_OK hwnd=$hwnd"
  }
  "click" {
    $r = Get-WinRect
    Click-At ($r.L + $X) ($r.T + $Y)
    Write-Output "CLICKED:$X,$Y"
  }
  "clickabs" {
    Click-At $X $Y
    Write-Output "CLICKED_ABS:$X,$Y"
  }
  "type" {
    Send-Key $Text
    Write-Output "TYPED:$Text"
  }
  "key" {
    Send-Key $Text
    Write-Output "KEY:$Text"
  }
  "shot" {
    Take-Shot
  }
  "winrect" {
    $r = Get-WinRect
    Write-Output "RECT:$($r.L),$($r.T),$($r.R),$($r.B)"
  }
  default { Write-Output "ERR:UNKNOWN_ACTION" }
}
