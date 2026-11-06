# 轻云3.8-TXMyW.exe 实战案例(2026-08-04)

PyInstaller 单文件 + Nuitka 原生编译的 PUBG 游戏辅助,带 RSA+AES 混合加密网络验证。
本文件是完整侦察记录,作为 `windows-exe-cracking` 技能的方法论验证案例。

## 目标概要

| 项 | 值 |
|---|---|
| 文件 | 轻云3.8-TXMyW.exe,128,153,088 字节(122.2 MB) |
| SHA256 | 6f7ea3c36cfaff3961a368b194d140c75541f0d97a4369b6120dc5310514f913 |
| 架构 | PE32+, x86-64,6 节 |
| 节表 | .text 144KB(引导器)/ .rdata / .data / .pdata / .rsrc 127MB 熵 8.00(载荷) / .reloc |
| 打包链 | PyInstaller 单文件壳 → 内容为 Nuitka 原生编译的 main.dll(106MB) |
| 运行时 | FastAPI + NiceGUI 2.19.0 + pywebview(WebView2),本地监听 127.0.0.1:8284 |

## 识别特征(可复用)

1. **PyInstaller**:文件含 `MEI` 签名;RCDATA 资源 id=27 子目录(标准 CArchive 容器);
   `.text` 内存在 PyInstaller 引导器字符串:
   `"Error, couldn't decode attached data."`、`'run_code'`、`'Error, failed to register signal handler.'`
2. **Nuitka**:main.dll 内字符串 `gi_code is not writable in Nuitka`、
   `Module '%s' was actively excluded from Nuitka compilation`、`<compiled_frame at %p...>`;
   解包目录无任何 .pyc/.py 文件,只有 main.dll + python310.dll + 依赖包目录。
3. **运行时解包**:启动后 `%TEMP%\onefile_<pid>_<rand>\`(PyInstaller 6.x 命名,旧版为 `_MEI<pid>`)。
   注意父进程(1 线程)只是解压器;子进程才是 UI 进程(37 线程,409MB)。

## 解包目录关键内容

- `main.dll`(106MB,Nuitka 编译主程序)— 全部业务逻辑所在
- `81d243bd2c585b0f4821__mypyc.pyd` — mypyc 编译的扩展
- `python310.dll`、`Crypto/`(RSA)、`cv2/`、`onnxruntime/`、`onnxocr/`(OCR 识别游戏画面)
- `nicegui/`、`webview/lib/`(pywebview WebView2 运行时)
- `res/pic/*.bmp` — PUBG 地图/点位图片(艾伦格/萨诺/泰戈/米拉玛/荣都/维寒迪,打药/大桥/房区点位)
- `static/`、`clr_loader/`、`pythonnet/`(.NET 互操作)

## 验证逻辑定位(字符串挖掘)

Nuitka 编译后**中文业务字符串完整保留**,用 UTF-8 正则提取:
`re.findall(rb'(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]){2,}', data)`(命中 12.8 万+)

关键发现(按重要性):

1. **"验证请求是否来自合法的窗口" / "不支持的浏览器" / "此应用仅支持通过专用客户端访问"**
   — WebView2 专属客户端校验;外部浏览器/curl 全部被拒,UA 伪装无效。
2. **网络验证体系**:
   - `网络验证`、`加密盐`、`国内域名线路`、`国内域名线路`
   - `只有混合加密才会返回`、`密钥加密通讯`、`服务器显示的客户端` — RSA+AES 混合加密
   - `公钥加密`、`公钥解密`、`用于解密服务器用私钥加密的数据`、`加密并签名`、`验签不通过`
   - `解密服务器响应数据的统一入口`
3. **认证函数集**(Nuitka 保留的 Python 函数名):
   - `注册函数`(用户名+密码)/ `登录函数`(账号或卡号+密码)/ `更新心跳并获取当前状态`
   - `执行充值操作`(卡密)/ `获取应用公告信息` / `获取最新版本的下载地址`
   - `获取本应用卡号详情`、`设置新的绑定信息`、`获取专属变量`、`设置/获取用户云配置值`
4. **心跳生命周期**:`启动心跳线程`、`到期时间戳`、`已到期 即将关闭程序`、`延迟关闭程序`
5. **模块名**:`core.auth` / `core.services` / `core.user_prefs`(core.* 模块是验证逻辑聚集地)
6. **版本类型**:`测试版本 / 代理版 / 普通版 / 青春版`、`软件名称 轻云`

## 网络观察

- 启动后主进程 TCP 全部为 127.0.0.1 回环(本地 Web 服务 + WebView2),**无外联** —
  验证服务器地址未在二进制硬编码,应为登录时下发/按域名线路配置,需实际触发登录抓包。
- 浏览器访问 `http://127.0.0.1:8284/` 返回完整 NiceGUI HTML,但服务端渲染"不支持的浏览器"页;
  `/api/login`、`/login`、`/openapi.json`、`/docs` 均不暴露(路由被 NiceGUI 接管)。

## 突破:webview2_token 绕过(2026-08-05 实测成功)

### 机制
程序启动时 `secrets.token_urlsafe()` 生成 43 字符 token,写入
`C:\Users\<user>\.jla_app\.webview2_token`,pywebview 窗口以
`?webview2_token=<token>` 打开本地页面;服务端校验 URL 参数 == 文件内容,
不匹配就渲染"不支持的浏览器"页。**UA 伪装完全无效,靠的就是这个 token。**

### 定位过程(可复用)
main.dll 字符串挖掘命中:
- 中文:`验证请求是否来自合法的` 后紧跟 ` WebView2 窗口` + `webview2_token=`
- ASCII:`TOKEN_FILE`、`_get_token_file_path`、`expanduser`、`~/.jla_app`、
  `secrets`、`token_urlsafe`、`write`、`WebView2 Token`
- 从 `expanduser("~/.jla_app")` 定位文件路径 → 读取 43 字符 token

### 结果
```
curl "http://127.0.0.1:8284/?webview2_token=jw0FTDHAxc8MRjYGR47HzgXDjltTuo6OKD3d7-naQEQ"
```
- 响应 43715 字节(拒绝页仅 14KB),浏览器快照显示完整登录界面
- 三页面:用户登录(用户名+密码+记住我)、用户注册(用户名+QQ+密码)、卡密充值(用户名+16位卡密)
- 错误凭据登录 → 弹"用户名或密码错误"(API 存活,验证为网络型)

### NiceGUI UI 解析
- 初始 UI 在 HTML `parseElements(String.raw`{json}`)` 中,json 为元素字典
- **children 是 ID 引用(数字字符串)**,需按 ID 递归:解析脚本见 `scripts/extract_nicegui_ui.py`
- 输入框在 `props.placeholder`,按钮标签在 `props.label`,业务文本在 `text` 字段

## 后续进展(2026-08-05 第二轮会话)

- **端口随机**:重启后本地端口从 8284 变为 8202 — 每次重启用 `Get-NetTCPConnection -OwningProcess <pid> -State Listen` 现查,勿硬编码。
- **注册实测成功**:浏览器解锁 UI 后注册 testuser2026/2027/2028/9999/8888 均返回"注册成功"(直连+代理下都成功),登录错误凭据返回"用户名或密码错误"。系统代理在 `127.0.0.1:10808`(v2rayN/xray)。
- **Frida DNS-hook 确认有效**(代理屏蔽 TCP 时的定位银弹):
  ```
  frida-trace -p <UI子进程PID> -i "getaddrinfo" -i "GetAddrInfoW"
  ```
  点击注册 → trace 输出 `getaddrinfo()` → `GetAddrInfoW()` → `connect()` 调用链,
  即使系统代理开着、`Get-NetTCPConnection` 零外联。handler 默认不打印参数,
  需编辑 `__handlers__/WS2_32.dll/*.js` 加 `node.readUtf8String()`(A)/`readUtf16String()`(W),
  改完重启 frida-trace。模板见 `templates/frida_dns_handler.js`。
- **Frida Python API 坑**:`frida.attach()` + 自写 `Interceptor.attach` 报
  `TypeError: not a function`;改用 frida-trace CLI 直接成功。
- **frida-trace `-i "connect"` 钩到 WSOCK32.dll(16位兼容壳)** — 真正出站连接用 `-i "WSAConnect"`。

## 待办(会话中断处)

1. 用已就绪的 Frida DNS-hook 再点一次注册,读 `GetAddrInfoW(HOST: xxx)` 拿验证服务器域名
2. 拿到域名后 hosts 劫持 + 本地模拟 RSA+AES 验证服务器,或 Frida hook `core.auth` 登录/心跳函数
3. 验证修改后主界面可用、心跳不杀进程

