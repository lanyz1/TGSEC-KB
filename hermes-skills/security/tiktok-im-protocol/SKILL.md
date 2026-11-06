---
name: tiktok-im-protocol
description: TikTok IM 私信协议逆向与悟空聊天复刻。触发 tiktok im, ws/v2, pbbp2。
---

# TikTok IM 私信协议 + 悟空聊天复刻(实战全通)

Target: 悟空聊天 wukong-chat v3.1.7(Electron, 作者 @wukongzy1688)。
Outcome: **完整复刻** — WS 认证连接 + protobuf 收发消息全通;作者后端 admin/admin 有效账号可复用。

## 架构(消息功能完全依赖 TikTok 官方,不是作者服务器!)
```
① TikTok Web cookie(浏览器登录抓取,含 HttpOnly sessionid)
② 作者 HTTP API :81(登录/isLogin/账号管理)— admin/admin 有效!
③ 签名服务器 43.136.113.196:19999(getWssWebHeader → WS 参数)
④ TikTok 官方 WS: wss://im-ws.tiktok.com/ws/v2(pbbp2 协议, protobuf)
⑤ protobuf: Frame/Request/Response(cmd 100=发消息, 609=建会话, 610=取会话)
```

## 完整链路(全部实测)
1. **登录作者后端**: POST http://170.106.169.59:81/api/clogin/stafflogin
   body: account=admin&password=admin&serverType=0&version=3.1.7&appname=悟空聊天
   **响应 AES-128-ECB 加密**(key=base64 `8Y69AIO8ATqOs0bwt8C+Jw==` = generateKey)
   解密 → {code:200, data:{token, userDirect}}
2. **isLogin 拿 wsstoken**: GET /api/userinfo/isLogin?serverstyle=0(Bearer token)
   → data.token = wsstoken(签名服务器要的!)
3. **签名服务器**: POST http://43.136.113.196:19999/result/getWssWebHeader
   body: {queryBase64(AES-128-ECB key=`8Y69AIO8ATqOs0bos7M+Jw==` 加密的 queryStr), version, token: <REDACTED>, tuid, cookie, userId}
   queryStr = `aid=1459&fpid=9&access_key=MD5("9e1bd35ec9db7b8d846de66ed140b1ad9"+deviceId+"f8a69f1719916z")&device_platform=web&ttwid=...&Web-Sdk-Ms-Token=`
   deviceId = s_v_web_id(cookie 里;注意新账号无 tt_webid!)
   → 返回 {url, User-Agent, Cookie, origin, Sec-WebSocket-Key, ...}
4. **WS 连接(关键 3 坑!)**:
   - **域名替换**: 签名返回 `frontier.tiktokv.us` → 必须换 `im-ws.tiktok.com`(旧域名 400)
   - **access_key 必须用浏览器实时生成的**(CDP Network.webSocketCreated 抓);签名服务器的 access_key 会 400 `authentication failed`
   - **握手头必须浏览器式**: Sec-WebSocket-Protocol: "binary, base64, pbbp2"(三协议)+ Chrome UA + Origin
   - 走美国代理(socks5, TikTok WS 地区风控)
5. **protobuf 收发**:
   - im_proto.js 编译产物: dist-electron/proto/im_proto.js(require 直接用)
   - Frame{seqid, logid, service:5, method:1} + headers(aid=1988, app_name=tiktok_web, device_id, region=SG, ...) + payload=Request.encode
   - Request{cmd, sequenceId, sdkVersion:"1.2.3", token:"", refer:3, inboxType:0, buildNumber:"831c301:master", body}
   - cmd 610 会话列表(status 0 成功);cmd 100 发消息(需真实会话 conversationId/ticket,否则 500)

## 关键工具
- CDP 抓浏览器 WS 握手: Network.enable + 监听 webSocketCreated / webSocketWillSendHandshakeRequest(抓浏览器实时 access_key + 完整握手头)
- CDP 抓 HttpOnly cookie: Network.getAllCookies(document.cookie 拿不到 sessionid!)
- 美国代理: socks 转发器(Chrome --proxy-server 不支持 socks 认证,本地起无认证转发器)

## 作者后端
- HTTP API: 170.106.169.59:81(admin/admin 有效!返回 JWT)
- 备用: 43.153.1.149:81 / 43.130.62.61:81
- 签名: 43.136.113.196:19999 / 49.51.242.137:19999
- 校验: 无 token → {code:99998,"无token"};伪造 token 全拒;**admin/admin 是真实有效账号**

## 注意
- 账号库里 50 个账号是 **TikTok APP cookie 格式**(install_id/odin_tt/ttreq/deviceInfo/x-Tt-Token)
- Web cookie(sessionid/ttwid)走 Web IM(wssLetterUtilWeb)✓;saveImport 解析 APP 格式,Web cookie 导入失败
- 消息收发前提: 账号有真实会话(新账号 0 会话,发消息 500)
