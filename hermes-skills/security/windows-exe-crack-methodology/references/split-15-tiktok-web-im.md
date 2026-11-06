## TikTok Web IM 复刻(消息功能链路,本会话实测打通)
适用: 任何 TikTok 私信/IM 采集工具(如悟空聊天)的消息功能复刻。完整链路 = 登录作者后端 → isLogin 拿 wsstoken → 签名服务器生成 WS 参数 → 连接 TikTok 官方 WS(pbbp2 协议)。
- **作者后端弱口令可碰**: 悟空聊天 `account=admin, password=admin` 直接登录成功返回真实 JWT(用真 token 调作者 API + 签名服务器)。登录响应是 **AES-128-ECB 加密 base64**(key 在源码 aESUtil.ts,generateKey='8Y69AIO8ATqOs0bwt8C+Jw==')→ Node crypto 解密得 {token, userDirect}。
- **签名服务器**: `POST {SignIP}:19999/result/getWssWebHeader`,body `{queryBase64(AES-ECB(queryStr, generateKey3)), version, token: <REDACTED>, tuid, cookie, userId}` → 返回 {url, Cookie(完整), Sec-WebSocket-Key, Sec-WebSocket-Protocol...}。queryStr 含 `access_key=MD5(盐+deviceId+盐)`(源码盐串在 wssLetterUtilWeb.ts)。
- **WS 连接三大坑(400 排查顺序,全踩过)**:
  1. **域名**: 签名服务器给 `frontier.tiktokv.us`(旧)→ 400;浏览器实际用 `im-ws.tiktok.com`,替换域名。
  2. **access_key 必须用浏览器实时生成的**(浏览器打开的 WS url 里 32hex)→ 签名服务器算的 → 400 `authentication failed`。获取: CDP `Network.webSocketCreated` 抓浏览器 WS url。
  3. **握手头浏览器式**: `Sec-WebSocket-Protocol: "binary, base64, pbbp2"`(三个子协议)+ Chrome UA。只传 pbbp2 → 400。TLS 用 min/maxVersion TLSv1.2 + ALPNProtocols ['http/1.1']。
  - 三坑全过 → WS 认证成功(closed 1006 = 后续 protobuf 帧格式错,连接本身成功)。
- **TikTok 登录风控**: 数据中心代理 IP(如 Tokala Communications)→ 扫码登录必失败。用**住宅/ISP 代理**(ipinfo.org 查 org 非 hosting)。Chrome `--proxy-server` 不支持 SOCKS5 认证 → 本地无认证转发器(socks_forward.py)再指定。手机无 TikTok APP → 用邮箱登录。
- **CDP 抓 HttpOnly cookie**: `document.cookie` 拿不到 sessionid(HttpOnly)→ `Network.enable` + `Network.getAllCookies`。
- 详情: `references/tiktok-im-replication.md`。

