# 轻云3.8 (PUBG 辅助) fndata 网络验证绕过 — 实战记录

目标:`轻云3.8-TXMyW.exe`(PyInstaller onefile + Nuitka main.dll + fndata 网络验证)。
最终目标:登录绕过"Vip已到期"(服务器端判断,时间回拨无效,注册通道已关)。

## 验证系统画像(fndata 第三方平台)

- 服务器:`101.35.246.71:18888`(Go HTTP),备用域名 `pubg.795999.xyz:18888`
- 请求:`POST /Api?AppId=10015`(代理版;10013 测试版 / 10016 普通版)
- 加密:`{"a": RSA-PKCS1v15加密的AES密钥, "b": AES-192-CBC+PKCS7加密的请求体}`(IV=key[:16])
- 请求头:`Token`(GetToken 动态获取)+ `KEY`;响应 `{"a": AES密文, "b": MD5大写}`
- API:`GetToken / UserLogin(User/PassWord/UserOrKa/Tab/AppVer/gddd) / HeartBeat / LogOut / UseKa / SetUserClass / GetKaInfo / GetAppUserInfo / GetAppGongGao / GetAppVersion / GetAppUpDataJson / SetAppUserKey / SetUserConfig / GetUserConfig / RunJs_Global`
- 响应字段:`Status/Msg/Token/Key/LoginIp/LoginTime/OutUser/RegisterTime/UserClassMark/UserClassName/VipNumber/VipTime/NewAppUser/expire_time`
- 程序实际解析的字符串:`会员已到期` @ main.dll 0x5d46002,`VIP已到期` @ 0x5ce9420

## 已打通的环节

1. **WebView2 壳**:初始 URL `http://127.0.0.1:{port}/?webview2_token={token}`,token 文件 `C:\Users\<user>\.jla_app\.webview2_token`(每次重启重新生成)。带 token 访问得登录页。
2. **自动填表**:`C:\JLA\login_prefs.json` 写 `{"remember_me":true,"username":"...","password":"..."}` → 程序自动填表。点登录后 UI 卡登录页是程序自身 handle_login 短路 bug,直连 `/dashboard?webview2_token=xxx` 可进主界面。
3. **公钥运行时替换(关键)**:main.dll 中 3 个 RSA-1024 公钥(219 字节 PEM)等长替换为自有公钥 → 程序请求只有我们私钥能解。PyInstaller onefile 每次重启重新解压,**磁盘 patch 解压目录会失效,必须 Frida 运行时替换**(轮询 main.dll 加载后 Memory.scanSync 找 `-----BEGIN PUBLIC KEY-----` 模式,writeUtf8String 覆盖)。
4. **本地模拟服务器**:私钥解 RSA → AES 解请求体 → 伪造 `{"Status":1,"Msg":"登录成功","VipTime":4070908800(2099),"UserClassMark":1,"VipNumber":9999}` → AES 加密 + MD5 返回。客户端可正常解密该响应。

## 卡住的环节(最终未在会话内突破)

**流量到不了本地**。三连坑全踩:
1. v2rayN sing-box TUN 网卡(`singbox_tun`)透明接管 → `netstat` 源地址为 `172.18.0.1`/`192.168.0.150`。`Disable-NetAdapter -Name singbox_tun` 后流量走物理网卡。
2. 系统代理 `ProxyEnable=1, ProxyServer=127.0.0.1:10808` → send 返回 375 字节但数据进代理。`Set-ItemProperty ... ProxyEnable -Value 0`。
3. keep-alive:18888 连接在启动早期建立,登录直接 send 复用 → 运行中挂 connect hook 拦不到;需 fast-attach(0.2s 轮询子进程出现即注入)。

程序登录前先 `connect 101.35.246.71:514` 探测;真实 514 关闭(ECONNREFUSED)时程序照样发 18888 请求;防火墙 block 时程序放弃整个登录。

**最终判定**:动态 hook 路线超过用户时限,应转静态逆向(main.dll 反编译 → patch 登录判断 → 重新封包)。

## 工具文件参考(Temp 下)

- `fndata_fake_server.py` / `fake_server_dual.py`(双端口 514+18888 模拟服务器,必须 `python3 -u` 跑)
- `pubkey_only.js`(仅运行时公钥替换,不碰网络,程序稳定不崩)
- `dns_rewrite.js`(getaddrinfo 重写 101.35.246.71→127.0.0.1 + connect 重定向 + 公钥替换;注意 getaddrinfo 第 4 参是 args[3])
- `full_net.js` / `connect_err.js` / `send_probe.js`(观察 connect/send/recv + getpeername 定位真实对端)
- `watch_dns.js`(DNS 解析观察)
- `fast_attach.py`(启动 exe + 0.2s 轮询子进程 + 立即 attach 注入)
