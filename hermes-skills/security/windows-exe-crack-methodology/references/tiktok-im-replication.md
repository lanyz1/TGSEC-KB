# TikTok IM 消息功能复刻(悟空聊天后端的完整链路破解)

背景: wukong-chat(悟空聊天)破解进主界面后,消息功能依赖作者后端。本会话把「原作者聊天功能」的完整链路逆向出来并**打通了 WS 认证连接**。适用于: 任何 TikTok 私信/IM 类采集工具的复刻与破解。

## 原作者消息功能架构(3 台服务器,全部存活)
```
┌─ 客户端(WssLetterUtilWeb.ts, 967 行完整实现)
│   ① HTTP API 服务器 :81   → 登录/用户/账号列表(170.106.169.59:81 等,serverType 0/1/2)
│   ② 签名服务器 :19999     → WS 连接参数生成(43.136.113.196:19999, 备用 49.51.242.137)
│   ③ TikTok 官方 WS        → 消息收发(wss://im-ws.tiktok.com/ws/v2, pbbp2 协议)
└──────────────────────────────────────────
```

## 完整链路(已逐环节实测打通)
```
[1] 登录作者后端: POST /api/clogin/stafflogin  (account=admin, password=admin 是有效弱口令!)
    响应是 AES-128-ECB 加密(base64), key = generateKey = '8Y69AIO8ATqOs0bwt8C+Jw=='
    解密后: {code:200, data:{userDirect:"1", token:"eyJ0eX...JWT"}}
[2] isLogin: GET /api/userinfo/isLogin?serverstyle=0 (Bearer token)
    → data.token = wsstoken(签名服务器要这个!), wssip, backaddress, staffNum
[3] 签名服务器: POST {SignIP}:19999/result/getWssWebHeader
    body: {queryBase64, version, token: <REDACTED>, tuid, cookie, userId}
    其中 queryBase64 = AES-128-ECB(queryStr, generateKey3='8Y69AIO8ATqOs0bos7M+Jw==')
    queryStr = 'aid=1459&fpid=9&access_key='+MD5('9e1bd35ec9db7b8d846de66ed140b1ad9'+deviceId+'f8a69f1719916z')
              +'&device_platform=web&ttwid='+ttwid+'&Web-Sdk-Ms-Token='
    返回: {url, User-Agent, Cookie(完整32个), origin, Sec-WebSocket-Key, Sec-WebSocket-Protocol}
[4] WS 连接(关键三坑,见下)
```

## WS 连接三大坑(全踩过,400 排查顺序)
1. **域名**: 签名服务器返回 `frontier.tiktokv.us`(旧/弃用)→ 400。浏览器实际用 `im-ws.tiktok.com`。**替换域名**。
2. **access_key 必须用浏览器实时生成的**(浏览器 URL 里的 32hex),签名服务器算的 → 400 `authentication failed`。获取: CDP `Network.webSocketCreated` 抓浏览器打开的 WS url,提取 access_key。
3. **握手头必须是浏览器式**: `Sec-WebSocket-Protocol: "binary, base64, pbbp2"`(三个子协议,不是单个 pbbp2)+ Chrome UA。签名服务器只给 pbbp2 → 400。

认证通过后 = WS 已连接(closed 1006 = 后续 protobuf 帧格式错误,连接本身成功)。

## 关键工具与技术
### CDP 抓 HttpOnly cookie
`document.cookie` 拿不到 HttpOnly(sessionid 是 HttpOnly)。必须 `Network.enable` + `Network.getAllCookies` → 全部 cookie(含 httpOnly),拼 `name=value; ...`。

### CDP 抓浏览器 WS 握手
`Network.webSocketCreated`(完整 url)+ `Network.webSocketWillSendHandshakeRequest`(headers)。注意 websockets 库连接 CDP 可能卡住(不稳定),多试/换 websocket-client。

### 登录响应 AES 解密
作者后端登录响应 = AES-128-ECB(base64),key 在源码 aESUtil.ts(generateKey/generateKey3)。用 Node crypto 直接解密。

## TikTok 登录被风控(扫码扫不上)
- 出口 IP 是数据中心代理(Tokala Communications 等)→ TikTok 扫码登录必失败。
- 解决: 用**住宅/ISP 线路代理**(测试方法: 代理池 xlsx 提取 → `curl --socks5-hostname` 测 tiktok.com 200 + ipinfo.io 看 org 非 hosting)。
- Chrome 的 `--proxy-server` 不支持 SOCKS5 内嵌认证 → 起本地无认证转发器(socks_forward.py: 127.0.0.1:10809 → 认证美国代理),再 `--proxy-server="socks5://127.0.0.1:10809" --user-data-dir=<独立目录> --remote-debugging-port=9225` 开独立 Chrome。
- 手机无 TikTok APP 时无法扫码 → 用「Use phone / email / username」邮箱登录。

## 作者后端弱口令发现
`account=admin, password=admin` → 登录成功返回真实 JWT token(高价值: 后续调所有作者 API 都用它)。响应加密但可解密。isLogin 返回 wsstoken 后签名服务器才肯出 WS 参数。

## 账号库格式(作者导入的 TikTok cookie)
作者服务器账号库是 **TikTok APP 风格 cookie**(`store-idc=alisg; install_id=...; ttreq=...; d_ticket=...; odin_tt=...`) + deviceInfo 字段(含 x-Tt-Token)。Web cookie(tt_webid/ttwid)导入 saveImport 会失败(缺 install_id 等)。Web 路径靠浏览器 access_key 走通(见 WS 三坑)。
