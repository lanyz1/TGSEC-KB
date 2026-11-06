# 悟空聊天(wukong-chat v3.1.7) 破解 + TikTok IM 部署复刻分析

Electron 应用(@wukongzy1688, 与 dashengcollect 同作者)。账号密码登录(非卡密)。
破解完成(进入主界面): patch 见 electron-asar-crack.md「实战补充」。本文档 = 消息功能实现链路 + 复刻「一模一样」的完整方案。

## 原作者聊天功能实现链路(源码完全还原)
```
① TikTok Web 账号 cookie(核心资产, 手动导入文本/文件 → 作者服务器 /account/saveImport 解析)
   cookie 含 sessionid(登录态) + tt_webid + ttwid
② 本地 webDeviceUtil.ts: 从 cookie 提取 deviceId(tt_webid) + ttwid
   构造 queryStr: aid=1459&fpid=9&access_key=MD5("9e1bd35ec9db7b8d..."+deviceId+"f8a69f...")&ttwid=...
③ 签名服务(关键): queryStr AES 加密 → POST http://{SignIP}:19999/result/getWssWebHeader
   → 返回 { url: wss://frontier.tiktokv.com/ws/v2?... , headers: {...} }(TikTok WS 连接的 xCylons/x-signature 签名, 作者服务器端算)
④ WssLetterUtilWeb.startSocket(headJson) → WebSocket 连接(pbbp2 子协议)
⑤ 消息收发: protobuf Frame/Request/Response(im_proto.ts, 18096 行, protoc 生成)
   cmd: 100=发消息 / 609=建会话 / 610=取会话; 文本/视频/卡片/贴纸/语音全类型
```

## 作者服务器(2026-08 实测全部存活)
- 签名服务: 43.136.113.196:19999(主) / 49.51.242.137:19999(备) — getWssWebHeader / myfriendListWebJson / getNewFollowWeb 等
- HTTP API: 170.106.169.59:81(serverType 0) / 43.153.1.149 / 43.130.62.61(serverType 1/2)
- 数据 API 签名(粉丝/关注等): 本地 XGorgon8404(electron/algorithm/xGorgon8404.ts, XGorgon84MD5)

## 复刻「一模一样」清单
| 组件 | 来源 | 状态 |
|---|---|---|
| TikTok 账号 cookie | 浏览器登录 TikTok 导出(独立指纹更稳) | ⭐ 用户需自己搞(核心资产) |
| WS 客户端 | 源码 electron/wss/wssLetterUtilWeb.ts(967行完整) | ✅ 复用 |
| protobuf 协议 | electron/proto/im_proto.ts(完整 schema) | ✅ 复用 |
| WS 连接签名 | 作者 19999 服务器 | ✅ 存活, 直接用 |
| 数据 API 签名 | 源码 XGorgon8404 | ✅ 已含 |
| HTTP API 服务器 | 作者 :81 或自建 73 端点 | ⚠️ 需有效账号 or 自建 |
| 前端/主进程 | 源码 + 破解补丁 | ✅ |

## 自建后端(不依赖作者)唯一难点
WS 连接签名(xCylons/X-Bogus) — 作者用服务器算。需逆向 TikTok 前端签名或抓包分析 getWssWebHeader 输入输出。数据 API 签名(XGorgon8404)源码已有。

## HTTP API 端点(作者后端 :81/api, 73 个)
- 认证: /api/clogin/stafflogin|chatlogin(POST account/password/serverType/version/appname → token/userDirect/backaddress)、/api/userinfo/isLogin?serverstyle=、/api/user/getUserConfig?appname=、/api/system/getAuthkey、/api/system/version
- 账号: /account/accountList、/account/clientSave、/account/deleteBatch、/api/accountGroup/slist、/chat/tag/user/save|batchSave、/link/manager/*、/link/play/*
- 营销/内容: /character/profile/*、/api/translate/translate、/api/feedback/*、/api/home/index、/api/user/getWord、/agent/list2
完整文档: D:\渗透\wukong_src\部署与API文档.md

## 注意
- 账号 sessionid 会过期, 需定期重新登录
- TikTok 风控: 新账号/异常登录可能触发验证
- 前端 request() 期望 axios 风格响应 `{ok, status, data:{code:200, data, msg}}`(破解伪造格式同此)

## 签名服务器接口实测(2026-08)
```json
POST http://43.136.113.196:19999/result/getWssWebHeader
{ "queryBase64": AES加密后的queryStr, "version": "3.1.7", "token": wsstoken,
  "tuid": 0, "cookie": "<TikTok wcookie>", "userId": 0 }
```
- AES-128-ECB(aESUtil.ts): key = `8Y69AIO8ATqOs0bos7M+Jw==`(base64 16字节), PKCS5 padding, 输出 base64。
- 实测: 服务器 200 响应,但**假 cookie → response 空**(服务器校验 cookie 真实性,有效才返回 WS 参数)。→ TikTok cookie 是硬性依赖,无法伪造。

## TikTok 登录风控(扫码扫不上的原因 + 解决)
- **症状**: tiktok.com 网页扫码登录,验证码永远过不了。
- **根因**: 出口 IP 是数据中心代理(实测 77.107.99.203 = AS401783 TOKALA COMMUNICATIONS = 代理/VPS 商段),被 TikTok 风控标记 → 扫码/验证码失效。
- **判断 IP 类型**: `curl ipinfo.io/<ip>/json` → org 含 hosting/digitalocean/aws/azure/google/vultr/linode/m247/datacamp/contabo/ovh = 数据中心(风控高危)。
- **解决**: 换**非数据中心 ISP 线路**(NTT AS2914 / GTT AS3257 等大型运营商 = 洛杉矶/波士顿线路,实测 TikTok 200 OK,风控风险低)。
- **代理池测试方法**(curl SOCKS5):
  ```bash
  curl -s -m 8 --socks5-hostname user:pass@host:port https://api.ipify.org   # 实际出口 IP
  curl -s -m 8 -o /dev/null -w '%{http_code}' --socks5-hostname user:pass@host:port https://www.tiktok.com  # 200 = 可用
  ```
- 其他失败原因: 手机无 TikTok APP(中国区商店没有)→ 无法扫码;改用邮箱登录或浏览器 cookie 方案。
- **cookie 获取**: 浏览器登录 tiktok.com → F12 Console → `document.cookie` → 完整 cookie 字符串(含 sessionid 等登录态)。
