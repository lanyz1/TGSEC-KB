# 轻云3.8-TXMyW.exe — worked reversing case (2026-08)

PUBG (绝地求生) auto-play assistant ("轻云", v3.8) with network card-key verification.
Task: bypass 卡密验证 and use normally. Environment: Windows 10, Hermes desktop, system
proxy running v2rayN (xray/sing-box).

## File profile

- `轻云3.8-TXMyW.exe`, 128,153,088 bytes, PE32+ x86-64
- SHA256: `6f7ea3c36cfaff3961a368b194d140c75541f0d97a4369b6120dc5310514f913`
- 6 sections; `.rsrc` = 127,935,488 bytes at entropy 8.0 (fully compressed/encrypted payload)
- `.text` = 144KB loader shell

## Packer identification (in order of evidence)

1. `MEI` byte signature at 0x13e354f + RCDATA resource id 27 → PyInstaller onefile
2. Bootloader strings in .text: "Error, couldn't decode attached data.", "run_code",
   "Error, failed to register signal handler."
3. **Nuitka tells** in main.dll strings: "gi_code is not writable in Nuitka",
   "was actively excluded from Nuitka compilation", `<compiled_frame at %p, file %R, line %d, code %S>`
   → Nuitka-compiled to native; NO .pyc anywhere → decompilation off the table

## Runtime extraction

- Launch via `Start-Process -PassThru`; PyInstaller 6.x extracted to
  `%TEMP%\onefile_364760_134303635302174727\` (NOT `_MEI*` — those were stale from other apps)
- Parent process = launcher only (1 thread, no window). Child = real app (window "轻云-PZWgN",
  37 threads, WebView2 subprocess). Track the child PID.
- Key files: `main.dll` (106MB, Nuitka main module), `81d243bd2c585b0f4821__mypyc.pyd`,
  python310.dll, Crypto/, cv2/, onnxruntime/, nicegui/, webview/ (pywebview libs)
- App architecture: FastAPI + NiceGUI 2.19.0, listens `127.0.0.1:8284`, rendered by pywebview/WebView2

## Business logic map (CJK string mining of main.dll)

- Module names: `core.auth`, `core.services`, `core.user_prefs`
- Functions: `create_auth_pages_container.<locals>.show_login / show_register / show_recharge`,
  `load_login_prefs`, `_create_exit_confirm_handler.<locals>.handler`
- Auth API surface: 注册函数 (username+password), 登录函数 (账号或卡号+password),
  更新心跳并获取当前状态, 执行充值操作 (卡密), 获取应用公告信息, 获取最新版本的下载地址
- Crypto: RSA+AES 混合加密 ("只有混合加密才会返回"), "用于解密服务器用私钥加密的数据",
  "密钥长度必须为 X 字节", "并生成校验值" (sign+verify), 加密盐 (encryption salt config)
- Lifecycle: 登录后启动心跳线程, 到期自动关程序 ("已到期 即将关闭程序"), 会员到期时间戳
- Versions: 测试版本/代理版/普通版/青春版
- 点位 feature map: PUBG maps 艾伦格/萨诺/泰戈/米拉玛/荣都/维寒迪, actions 打药/大桥/房区/伤害/跳伞
- Config: 本地 `~/.jla_app/` + 云端配置 (主界面配置/快捷键配置 saved to cloud)

## WebUI protection bypass (the critical unlock)

- Server rendered "不支持的浏览器 / 此应用仅支持通过专用客户端访问" for any non-WebView2 client
- String: `验证请求是否来自合法的 WebView2 窗口` + `webview2_token=`
- Mechanism: `secrets.token_urlsafe()` → write to `~/.jla_app/.webview2_token`
  (43 bytes, e.g. `jw0FTDHAxc8MRjYGR47HzgXDjltTuo6OKD3d7-naQEQ`)
- Bypass: `curl "http://127.0.0.1:8284/?webview2_token=$(cat ~/.jla_app/.webview2_token)"`
  → real login UI (43715 bytes vs 14KB blocked page)
- Browser (Hermes browser tools) then drives the live UI: username/password/登录/注册账号/卡密充值

## NiceGUI page parsing

- HTML embeds `parseElements(String.raw\`{...}\`)` — JSON UI tree with numeric child refs
- Must resolve children as `data[str(id)]`; naive recursion over nested dicts returns nothing
- Login page: 用户名 + 密码 + 记住我 + 忘记密码; Register: 用户名(≥6) + QQ号 + 密码(≥6) + 确认密码;
  Recharge: 用户名 + 16位充值卡密
- Wrong creds → "用户名或密码错误" alert (confirms auth API live)

## Verification server discovery (proxy-masked)

- Symptom: register "注册成功" but `Get-NetTCPConnection -OwningProcess <childPID>` shows
  only loopback (8284 listen + WebView2 conns). Zero outbound.
- Root cause: WinINET system proxy `ProxyEnable=1, ProxyServer=127.0.0.1:10808` (v2rayN xray).
  The proxy process owns the real outbound conns (14.119.66.81:30901, 113.105.x.x:443, 1.71.87.129:443).
- Capture: disable proxy (`Set-ItemProperty ... ProxyEnable -Value 0`), then
  `netsh trace start capture=yes maxsize=50 tracefile=...` + trigger register + `netsh trace stop`
- Parse: `Get-WinEvent -Path cap.etl` → NDIS-PacketCapture (EventID 1001), frame bytes at
  Properties[3]; extract TLS ClientHello SNI (see scripts/extract_tls_sni.py)
- SNI candidates: `fakainc.shop` (11 hits, Cloudflare) → resolved to a 发卡站 "无忧小店"
  (card-selling shop, likely the licensing backend or sale channel); remaining SNI was
  unrelated system traffic (deepseek, wechat, windows)
- Status at session end: server identity narrowed to fakainc.shop / 1.71.87.129:443 but not
  fully attributed; next steps = Frida hook on login/heartbeat or hosts hijack + local Flask
  simulator, with restart-aware token re-read (app regenerates .webview2_token each run).

## Environment facts that bit (Windows/MSYS)

- PowerShell `$pid` is read-only — use another variable name
- MSYS `/tmp/x.ps1` fails in PowerShell `-File`; write scripts to `C:\Users\...\Temp\`
- CJK filenames (轻云/极速v2) break MSYS `ls`/`find`; use PowerShell cmdlets for those paths
- Do not kill/restart the target process without user approval; restart regenerates the token
