---
name: windows-exe-cracking
description: "Bypass Windows EXE card-key/license verification."
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

# Windows EXE Cracking Skill

逆向破解 Windows 可执行程序,绕过卡密/授权/登录验证并使其正常可用。覆盖从侦察、打包器识别、运行时解包、定位验证逻辑到实施绕过的完整流程。不覆盖 APK/iOS/固件(另立流程);但 PyInstaller/Nuitka 识别技巧可复用于 Linux/macOS 打包产物。

## When to Use

- 用户给了一个 `.exe`(或打包脚本)要求绕过卡密验证、注册码、VIP 限制、登录墙
- 需要判断一个未知 PE 是否被 PyInstaller / Nuitka / UPX / NSIS / Electron 打包
- 需要定位"网络验证 + 心跳到期"型软件的授权逻辑
- 用户在做 CTF/渗透项目,第一个逆向目标通常是这类桌面辅助工具

## Prerequisites

- 目标文件在本地磁盘(Windows 主机可以直接运行解包)
- Python3 可用(用于 PE 解析、熵值、字符串提取)
- 运行目标 exe 前先备份原始文件;需要重启/杀进程前先告知用户
- 若目标是 Nuitka 编译,准备 Frida(动态 hook 优先)而非反编译器

## How to Run

1. 先跑 `scripts/pe_recon.py <file.exe>` 做 PE 侦察(节表 + 熵值 + 打包器签名)
2. 按下方 Quick Reference 判断打包方式,选择解包/定位路径
3. 运行目标,在 `%TEMP%` 找解包目录,分析真实载荷
4. 定位验证逻辑,选绕过方案,验证可用性

## Quick Reference

```
PE 侦察 → 打包器识别 → 运行时解包 → 字符串/反汇编定位验证 → 绕过 → 验证
```

| 特征 | 结论 |
|---|---|
| `.text` 很小(~100-200KB)但 `.rsrc` 巨大且熵≈8.0 | 单文件打包器,载荷在资源里,别直接解析,运行它 |
| 文件含 `MEI` 签名 / RCDATA id=27 资源 | PyInstaller 单文件 |
| `%TEMP%` 出现 `_MEI<pid>` 或 `onefile_<pid>_<rand>` 目录 | PyInstaller 解包目录(6.x 用 onefile_ 前缀) |
| DLL 内字符串含 `Nuitka`、`gi_code is not writable in Nuitka` | **Nuitka 原生编译**:无 .pyc,反编译工具全部无效 |
| 字符串含 `不支持的浏览器` / `仅支持通过专用客户端访问` | 本地 Web UI + "合法窗口"校验(见 Pitfalls) |
| 字符串含 `心跳`、`到期时间`、`加密盐`、`网络验证` | 网络验证型:服务器地址常为运行时下发,需抓包 |

## Procedure

### 1. 侦察(不运行)
- `scripts/pe_recon.py <file.exe>`:机器类型、节表、每节熵值、打包器签名
- 熵值 ≈8.0 的大节(尤其 `.rsrc`) = 压缩/加密载荷;`.text` 小 = 加载器外壳
- 记录 SHA256,保留原始文件

### 2. 识别打包方式
- **PyInstaller**:MEI 签名、RCDATA/27、运行时 `%TEMP%\_MEI<pid>` / `onefile_<pid>_<rand>`
- **Nuitka**:DLL 内 `Nuitka` 专属字符串;解包后无 `.pyc`,主逻辑在 `main.dll`(可能上百 MB)+ 可选 `*__mypyc.pyd`
- **Electron**:`app.asar` 签名,解 asar 找 JS 验证逻辑
- **NSIS/Inno**:安装包,先装再分析
- 判断错了就换:PyInstaller 6.x 的 onefile 目录命名与旧版不同

### 3. 运行时解包(Windows)
- `cmd //c start "" "目标.exe"`,等 5-15 秒(122MB 解压需要时间)
- 检查 `%TEMP%`:PyInstaller 6.x → `onefile_<pid>_<rand>`,旧版 → `_MEI<pid>`
- 解包目录里通常有:主逻辑 DLL、python*.dll、依赖包目录(Crypto/cv2/numpy 等)、`res/`、`static/`
- 用 `Get-Process` / `Get-CimInstance Win32_Process` 找到真实主进程(父进程常只是解压器,子进程才是 UI 进程)

### 4. 定位验证逻辑
- **字符串挖掘**(对 Nuitka 编译 DLL 有效!):
  - ASCII:`re.findall(rb'[\x20-\x7e]{4,}', data)`
  - **中文 UTF-8**(中国软件必查):`re.findall(rb'(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]){2,}', data)` — 中文业务字符串在 Nuitka 编译后完整保留
  - 模块名 `core.auth` / `core.services` / `core.user_prefs` 是验证逻辑聚集地
- **关键字**:login/register/recharge/heartbeat/expire/card/卡密/充值/到期/心跳/加密盐/网络验证/会员
- **网络验证特征**:`加密盐`、`只有混合加密才会返回`(RSA+AES)、`心跳线程`、`到期时间戳`、`服务器显示的客户端` —— 服务器地址可能不硬编码,而是运行时从云端配置下发
- 若程序是 FastAPI/NiceGUI + pywebview:本地 Web 服务,`Get-NetTCPConnection -State Listen -OwningProcess <pid>` 找端口,可尝试浏览器/curl 访问

### 4.5 绕过"合法窗口"校验(webview2_token 通用套路)
针对 pywebview + 本地 Web 服务型应用(轻云3.8 实测有效):
1. 服务端渲染"不支持的浏览器"页 = 有来源校验。在 main.dll 里搜 token 相关字符串:
   - ASCII: `webview2_token`、`TOKEN_FILE`、`get_token_file_path`、`token_urlsafe`
   - 中文: `验证请求是否来自合法的`(后面常跟 `WebView2 窗口` + `webview2_token=`)
2. 从字符串上下文定位 token 文件路径(如 `expanduser("~/.jla_app")` → `C:\Users\<user>\.jla_app\.webview2_token`)
3. 读取 token 文件内容(几十字节的 URL-safe base64)
4. 浏览器/curl 访问 `http://127.0.0.1:<port>/?webview2_token=<token>` → 校验通过,拿到真实登录/主界面
5. 之后可用浏览器工具完全操作 UI(填表、点登录/注册/充值按钮)

### 4.6 NiceGUI 页面解析
- 初始 UI 在页面 HTML 的 `parseElements(String.raw`{json}`)` 里,`{json}` 是元素字典
- **children 是 ID 引用(数字字符串),不是嵌套对象** — 解析时要按 ID 递归查 `data[str(nid)]`
- 业务文本在节点 `text` 字段,输入框在 `props.placeholder`;提取这些即可还原界面结构
- 错误提示(如"用户名或密码错误")通过 WebSocket 推送,不在初始 JSON 里,要看浏览器快照

### 4.7 Frida DNS-hook 定位验证服务器(代理屏蔽 TCP 时的银弹)

症状:程序注册/登录"成功",但 `Get-NetTCPConnection -OwningProcess <子进程PID>` 始终零外部连接(系统代理如 v2rayN/xray 在 `127.0.0.1:10808` 屏蔽了直连)。此时**不要只盯 TCP**——程序在进程内照样调用 `getaddrinfo`/`GetAddrInfoW` 解析域名。用 frida-trace hook DNS 函数即可拿到验证服务器域名:

```bash
pip install frida frida-tools   # 首次
# 附加到真实 UI 子进程(父进程只是解压器,1线程无窗口)
frida-trace -p <childPID> -i "getaddrinfo" -i "GetAddrInfoW"
```

自动生成 handler 在 `__handlers__/WS2_32.dll/getaddrinfo.js`(和 `GetAddrInfoW.js`),**默认不打印参数**。改为:

```js
onEnter(log, args, state) {
  var node = args[0];
  if (!node.isNull()) {
    log('getaddrinfo(HOST: ' + node.readUtf8String() + ')');   // A 版本
    // GetAddrInfoW 用 readUtf16String()
  }
}
```

**改完 handler 必须重启 frida-trace**(handler 在启动时加载)。然后在应用里触发一次注册/登录(浏览器已解锁 UI 时直接点按钮),trace 里就会出现 `GetAddrInfoW(HOST: xxx.xxx)` → 验证服务器域名到手。

已实测(轻云3.8):点击注册按钮 → `getaddrinfo()` → `GetAddrInfoW()` → `connect()` 调用链完整出现在 trace 中,即使系统代理开着。模板见 `templates/frida_dns_handler.js`。

### 4.8 fndata 类网络验证平台协议提取(DNS 定位后的下一步)

DNS hook 拿到服务器 IP 后,**全套加密凭证几乎都硬编码在同一 DLL 的 API URL 字符串附近**。在 main.dll 里搜 `http://<ip>:<port>`(或直接搜 IP 字节串如 `b'101.35.246.71'`),dump 该地址前后 4-8KB 的字符串,一次就能拿到:

```
API:      http://<ip>:18888/Api?AppId=<appid>   # 每个版本一个 AppId
Token:    <32位大写base32样>                      # 请求头 Token
KEY:      <8位短key>                             # 请求头 KEY
AES密钥:   <24位base64样>                         # 加密盐(请求体用 AES)
RSA公钥:   -----BEGIN PUBLIC KEY----- ...         # 每套 AppId 一个(1024位)
```

再搜 API 函数名(`UserLogin`/`HeartBeat`/`LogOut`/`GetKaInfo`/`SetUserClass`/`GetAppUserInfo`)和中文业务串(`登录函数`/`心跳`/`卡密充值`/`到期时间戳`)还原完整接口面与响应字段(`Token`/`VipTime`/`UserClassMark`/`LoginIp`/`LoginTime`)。请求体是 **RSA 包 AES 密钥 + AES 加密请求体** 的混合加密,但请求头 Token/KEY 是明文。

**服务器探测技巧:**
- GET `/Api?AppId=xxx` 返回 Go 风格 `404 page not found` **不代表服务器死**——该 API 只收 POST
- `POST /Api?AppId=xxx` + `Token`/`KEY` 头 + `{}` 空体,返回 `{"Time":...,"Status":106,"Msg":"Token无效"}` → 服务器活着且在校验头;Status 码表常能在 DLL 中文串里挖到

### 4.9 Frida CLI 脚本 hook send/recv 抓明文请求

frida-trace 只能看函数名+自定义 handler;要抓**实际发出的 HTTP 请求明文/响应**,用 `frida -p <pid> -l script.js`(CLI 加载脚本)hook `ws2_32!send`/`recv`:

```js
var mod = Process.findModuleByName('ws2_32.dll');          // 用 Process API,不用全局 Module
var sendPtr = mod.getExportByName('send');
Interceptor.attach(sendPtr, {
  onEnter: function (args) {
    var len = parseInt(args[2].toString());                 // 别用 args[2].toInt32(),可能 not a function
    if (len > 0 && len < 100000) {
      var bytes = args[1].readByteArray(len > 2048 ? 2048 : len);
      // 转 ascii,若含 POST/GET/{ 就 send() 出来
    }
  }
});
```

- **Frida Python API(`frida.attach()` + `create_script`)在部分目标进程报 `TypeError: not a function`**,`frida -p <pid> -l <script.js>` CLI 方式更稳
- `Module.findExportByName` 在 CLI 脚本里也可能 not a function → 用 `Process.findModuleByName(name).getExportByName(exp)`
- hook 完去浏览器/UI 触发操作,输出文件里就能看到明文 HTTP 请求头(注意 body 是 AES 密文,但头/URL/JSON 结构可见)

## 5. 绕过(按优先级)
1. **最简 patch**:改跳转 JE↔JNE / NOP 失败分支(仅原生小程序可行)
2. **Frida 动态 hook**(Nuitka 编译首选):Hook 登录/心跳/充值函数直接改返回值,不改文件
3. **网络模拟**:抓到验证服务器后,hosts 劫持 + 本地 Flask 模拟(注意 RSA 双向加密时需逆向出协议)
4. **注册机**:算法在本地时重现算法

### 6. 验证
- 修改版能进入主界面、核心功能可用
- 记录原版 vs 修改版差异(offset、原始字节、修改字节)
- 确认心跳/到期检测不会中途杀程序

## Pitfalls

- **Nuitka = 无 .pyc**:不要浪费时间跑 pyinstxtractor/decompyle3;直接动态 hook 或读字符串+反汇编
- **.rsrc 熵 8.0 无法直接解**:唯一可靠解包方式是运行它,然后从 `%TEMP%` 拿解包目录
- **"合法窗口"校验(已破解,通用套路)**:pywebview/WebView2 应用对浏览器/curl 直接渲染"不支持的浏览器"页,UA 伪装无效。**实测机制**:程序启动时用 `secrets.token_urlsafe()` 生成 token,写入磁盘文件(如 `~/.jla_app/.webview2_token`),pywebview 窗口以 `?webview2_token=<token>` 打开页面,服务端校验 URL 参数与文件内容一致。**绕过**:在 main.dll 字符串中搜 `TOKEN_FILE` / `_get_token_file_path` / `expanduser("~/.xxx")` 定位 token 文件路径 → 读取内容 → 浏览器访问 `http://127.0.0.1:<port>/?webview2_token=<token>` 即通过校验,可完全操控 UI。详见 Procedure 第 4.5 节。
- **API 端点不暴露**:NiceGUI/FastAPI 会接管所有路由,`/api/login`、`/openapi.json` 可能 404 或返回 SPA HTML;不要假设 REST 端点存在
- **中文软件**:只用 ASCII 字符串挖掘会漏掉全部业务逻辑,必须跑 UTF-8 中文正则
- **验证服务器非硬编码**:二进制里可能没有域名/IP;需要程序实际发起登录请求时抓包(输入错误卡密触发一次登录)
- **登录失败可能不发外联请求**:实测错误凭据登录返回"用户名或密码错误",但主进程无任何外部 TCP 连接(校验在本地拦截)。要抓验证服务器,需用浏览器操作触发**注册**或拿到合法账号再登录;持续后台监控 `Get-NetTCPConnection -OwningProcess <子进程PID>` 过滤非回环地址,同时触发操作
- **PowerShell 只认 Windows 路径**:`powershell -File /tmp/xxx.ps1` 报"does not exist"(MSYS `/tmp` 不等于 Windows `C:\Users\...\Temp`)。先 `cat > /c/Users/<user>/AppData/Local/Temp/xxx.ps1` 再引用完整 Windows 路径
- **PowerShell `$pid` 是只读保留变量**:用 `$procId` 等自定义变量名,否则报 "Cannot overwrite variable PID because it is read-only"
- **父进程≠主进程**:PyInstaller 单文件父进程(1 线程、无窗口)只是解压器;真正 UI 进程是子进程(30+ 线程、有 MainWindowTitle)。监控网络/内存要看子进程 PID
- **本地 Web 端口是随机的**:NiceGUI/FastAPI 应用每次启动端口可能不同(轻云3.8 第一次 8284,重启后 8202)。不要硬编码端口,每次用 `Get-NetTCPConnection -OwningProcess <pid> -State Listen` 现查
- **frida-trace `-i "connect"` 会 hook 到 WSOCK32.dll(16位兼容壳)而非 WS2_32.dll**:要 hook 真正的出站连接用 `-i "WSAConnect"`;DNS 用 `-i "getaddrinfo"` / `-i "GetAddrInfoW"`
- **frida-trace handler 改完不生效**:handler 只在启动时加载,编辑 `__handlers__/WS2_32.dll/*.js` 后必须重启 frida-trace
- **Frida Python API 可能报 `TypeError: not a function`**:`frida.attach()` + `Interceptor.attach` 在部分版本/目标进程上有兼容问题,直接改用 frida-trace CLI 更稳
- 运行目标 exe 前先备份;不擅自 kill 用户进程

## Verification

- `scripts/pe_recon.py` 对已知 PyInstaller/Nuitka 样本输出符合预期(节表、熵值、签名)
- 对目标完成:识别打包方式 → 解包 → 定位验证函数 → 绕过 → 主界面可用
- 每个关键结论(打包器、验证类型、服务器地址)都要有运行时证据,不靠猜测

## Support Files

- `scripts/pe_recon.py` — PE 侦察脚本:节表 + 熵值 + 打包器签名
- `scripts/extract_nicegui_ui.py` — 从保存的 NiceGUI 页面 HTML 提取初始 UI 结构(文本/输入框/按钮,按 ID 递归)
- `templates/frida_dns_handler.js` — Frida DNS hook 模板:代理屏蔽 TCP 时定位验证服务器域名(见 Procedure 4.7)
- `references/qingyun-38-case.md` — 轻云3.8 实战案例:PyInstaller+Nuitka 识别、解包、字符串挖掘、webview2_token 绕过、验证架构的完整记录
- `references/fndata-network-verification.md` — fndata 类网络验证平台协议知识库:API 端点/AppId、硬编码 Token/KEY/AES/RSA 凭证、API 函数清单、响应结构与加密流程(见 Procedure 4.8)
