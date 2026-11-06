# 已登录浏览器窗口接管(无 CDP 时自动化用户已登录的浏览器)

> 2026-08-09 实战验证(Shodan 搜索页 / 独角兽SCRM 分享页)
> 场景: 用户已在自己 Chrome 登录了目标站(Shodan/Censys/管理后台),但该 Chrome 没开 CDP 端口。重启会丢登录态或要求重登 —— 用 Windows UI Automation 直接驱动现有窗口,不重启、不丢 session。

## 适用场景

- 目标站需要登录态,但用户已在普通 Chrome 登录(未开 --remote-debugging-port)
- computer_use/cua-driver 不可用时(后台驱动不可用)
- 需要批量翻页抓取已登录站点的数据(如 Shodan 搜索 1380 结果但免费版只显示 2 页)
- 需要从已登录页面提取 localStorage 里的 token(分享页/后台自动发放的会话凭证)

## 1. 找到已登录的 Chrome 窗口

```powershell
Get-Process chrome | Where-Object { $_.MainWindowTitle -ne "" } | Select Id, MainWindowTitle
# 标题含目标站名 = 已登录窗口, 记下 PID
# 例: 'http.title:"bot" http.html:"telegram" - Shodan Search - Google Chrome' → PID 1027404
```

注意 bash 里 `$_` 会被吃掉,用 python subprocess 调 powershell 或写成 .ps1 文件。

## 2. UI Automation 读取窗口内容(无需 CDP)

```powershell
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc = Get-Process -Id <PID>
$hwnd = $proc.MainWindowHandle
$root = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
foreach ($el in $all) {
    $name = $el.Current.Name
    if ($name -and $name.Length -gt 0) {
        Write-Output ("[" + $el.Current.ControlType.ProgrammaticName + "] " + $name)
    }
}
```

可读到: 页面统计(TOTAL RESULTS 1380)、搜索项标题/IP、地址栏 Edit 控件(AutomationId=view_1012)、按钮。结果列表逐条读太慢 —— 截图 + vision OCR 更快。

## 3. 截图 + vision OCR 批量提取

```powershell
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public struct RECT { public int Left, Top, Right, Bottom; }
public class W32 { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect); }
"@
$rect = New-Object RECT
[W32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left; $h = $rect.Bottom - $rect.Top
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
$bmp.Save("C:\path\shot.png", [System.Drawing.Imaging.ImageFormat]::Png)
```

然后 `python vision-api.py <png> "列出所有结果条目(IP/标题)"` 提取。每页截图一张,循环翻页。

## 4. 地址栏翻页(SendKeys,无需 CDP)

```powershell
Add-Type -AssemblyName System.Windows.Forms
[Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id)   # 激活窗口
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("^l")             # Ctrl+L 聚焦地址栏
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("https://www.shodan.io/search?query=...&page=2")
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
```

⚠️ 坑: Shodan 是 SPA,地址栏输入 page=N 可能不触发路由(第 2 页和首页内容一样)。验证翻页是否生效: 截图对比第一项是否变化。

## 5. 从已登录页面提取 localStorage token(分享页/后台)

邀请分享链接免登录自动发放 token,存 localStorage:

```python
# CDP 方式(需要自己起一个 CDP Chrome, 或用已有 CDP):
await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
    "expression": "JSON.stringify(Object.fromEntries(Object.entries(localStorage)))"
}}))
# 例: 独角兽SCRM 分享页 → share_sessions_v1 = {"tokens": {"<shareId>": "<JWT>"}, "userInfos": {...}}
```

token 拿到后直接带 `Authorization: Bearer <token>` 调 API 拉数据(账号列表/粉丝统计/详情)。

## Pitfalls

- **Chrome 锁 DB**: 浏览器运行中 Cookies/sqlite 被锁(WinError 32),不能直接复制。要走 CDP Network.getAllCookies 或让用户手动登录
- **AppActivate 必须用 PID**: `[Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id)`;用窗口标题匹配可能失败
- **截图前窗口必须可见**: CopyFromScreen 截不到被遮挡的窗口;必要时先 SetForegroundWindow/AppActivate
- **SendKeys 中文/特殊字符**: URL 用 % 编码;SendWait 里 {} 是特殊字符(Enter={ENTER}),字面量花括号需双写
- **判断翻页成功**: 每页第一项应不同;相同 = 路由没切换,换滚动方式(WM_MOUSEWHEEL)或直接导航
- **Shodan 免费限制**: 即使翻页成功,免费账号第 3 页起显示"Purchase a Shodan membership" —— 这是平台限制不是脚本问题,精准词搜索才是正解

## 相关文件

- 本会话脚本: D:\博彩通杀\research\shodan_*.py / dujiao_*.py(窗口枚举/截图/翻页/token提取)
