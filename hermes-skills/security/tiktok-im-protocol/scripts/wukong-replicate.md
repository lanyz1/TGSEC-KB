# 悟空聊天/TikTok IM 复刻 - 一键脚本
# 用法: 1) 准备好 tk_cookie_full.txt(TikTok cookie) 2) 启动本地 socks 转发器(美国代理, 10809)
# 3) 修改 BROWSER_ACCESS_KEY(从 CDP Network.webSocketCreated 抓浏览器实时 access_key)
# 4) node replicate_ws5.js
# 依赖: asar_extracted/dist-electron/proto/im_proto.js + asar_extracted/node_modules(ws, socks-proxy-agent)

# 前置: 登录作者后端拿 token
POST http://170.106.169.59:81/api/clogin/stafflogin
Content-Type: application/x-www-form-urlencoded
account=admin&password=admin&serverType=0&version=3.1.7&appname=悟空聊天
# 响应 AES-128-ECB 解密(key: 8Y69AIO8ATqOs0bwt8C+Jw==) -> {code:200, data:{token}}

# isLogin 拿 wsstoken
GET http://170.106.169.59:81/api/userinfo/isLogin?serverstyle=0
Authorization: Bearer <token>
# -> data.token = <REDACTED>

# 签名服务器拿 WS 参数
POST http://43.136.113.196:19999/result/getWssWebHeader
{
  "queryBase64": AES-128-ECB(key 8Y69AIO8ATqOs0bos7M+Jw==).encrypt(queryStr),
  "version": "3.1.7",
  "token": wsstoken,
  "tuid": 用户uid(从 multi_sids cookie 取),
  "cookie": 完整TikTok cookie,
  "userId": 0
}
# queryStr = aid=1459&fpid=9&access_key=MD5("9e1bd35ec9db7b8d846de66ed140b1ad9"+deviceId+"f8a69f1719916z")&device_platform=web&ttwid=<ttwid>&Web-Sdk-Ms-Token=
# deviceId = s_v_web_id(cookie)

# WS 连接(关键):
# 1. url 域名 frontier.tiktokv.us -> im-ws.tiktok.com
# 2. access_key 换浏览器实时生成的(CDP 抓)
# 3. headers: Sec-WebSocket-Protocol: "binary, base64, pbbp2", Chrome UA, Origin
# 4. 走美国 socks5 代理
# 5. protobuf Frame(cmd 610 会话列表 / cmd 100 发消息), 复用 dist-electron/proto/im_proto.js
