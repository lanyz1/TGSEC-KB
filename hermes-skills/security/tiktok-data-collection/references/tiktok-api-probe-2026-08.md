# TikTok API 采集实测记录 (2026-08)

目标: 验证 TikTok 账号数据采集可行性。全部经本机代理(v2rayN 7897)实测。

## 环境
- 本机访问 TikTok 需代理(v2rayN: socks 10808 / http 7897)
- 匿名会话请求 `https://www.tiktok.com/` 会种下 ttwid/tt_csrf_token/tt_chain_token(全部 HttpOnly+Secure)

## 失败路径(记录判别信号)
| 尝试 | 结果 | 信号 |
|---|---|---|
| 无 Cookie `GET /api/user/detail/?uniqueId=x&aid=1988` | HTTP 200 空 body | 匿名被静默拦 |
| 匿名会话 Cookie(ttwid等) 同接口 | HTTP 200 空 body | 无登录态不够 |
| 完整参数(device_id/odinId/verifyFp/msToken...) 无 Cookie | HTTP 200 空 body / item_list 400 | 字段齐了仍需签名 |
| 真实登录 Cookie(sessionid/odin_tt/ttwid/msToken) Python requests 直连 | user/detail 空 body / item_list HTTP 400 `{"statusCode":10201,"statusMsg":"missing required fields..."}` | **签名拦截,伪装成缺字段** |
| 页面内 fetch(CDP 注入 Cookie 后) 简参数 | 同样 400 | 缺 secUid |
| `window.byted_acrawler.frontierSign(url)` 生成短 X-Bogus | 拼上后仍 400 | 短签名(16字符)不够,需完整 X-Gnarly |

## 成功路径
1. 用户信息: `GET https://www.tiktok.com/@handle` → `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON
   - `.__DEFAULT_SCOPE__.webapp.user-detail.userInfo.user` 含 uniqueId/nickname/signature/secUid/avatarLarger(大中小三档)/verified
   - `.__DEFAULT_SCOPE__.webapp.user-detail.userInfo.stats` 含 followerCount/followingCount/videoCount/heartCount
   - `.__DEFAULT_SCOPE__.webapp.app-context` 含 csrfToken/wid(webid)/odinId
2. 作品列表: CDP 注入 Cookie(Network.setCookies, domain=.tiktok.com, httpOnly:true) → 页面 reload → `Runtime.evaluate` 内 `fetch('/api/post/item_list/?uniqueId=xx&secUid=xx&count=20&cursor=0&aid=1988',{credentials:'include'})`
   - 实测: HTTP 200, 20 条/527KB, stats 含 playCount/diggCount/commentCount/collectCount
   - secUid 从 SSR 提取;URL 里 secUid 需 encodeURIComponent
   - 页面 fetch 自动带 X-Gnarly 签名(webmssdk.js 拦截器),无需手动签名

## CDP 要点
- Chrome 启动: `chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=...`
  - 无 `--remote-allow-origins=*` → WS 握手 403 "Rejected an incoming WebSocket connection from the http://127.0.0.1:9222 origin"
- 抓 Cookie: `Network.getAllCookies` → result.cookies[] 含 httpOnly 标志(console 拿不到的都在)
- 注入 Cookie: `Network.setCookies` {cookies:[{name,value,domain,path,httpOnly,secure}]}
- 探测页面签名对象: `Object.keys(window).filter(k=>/sign|acrawler|bogus|gnarly|mssdk/i.test(k))` → `byted_acrawler`
- webmssdk: `https://lf16-tiktok-web.tiktokcdn-us.com/obj/tiktok-web-tx/webmssdk/2.0.0.514/webmssdk.js`

## 用户侧抓 CK 工具(交付物)
- `C:\Users\Administrator\Desktop\ttck\` — 抓tk登录ck.bat(GBK+CRLF) + 抓tk_ck.py
- 依赖: 仅 websocket-client(pip), 无需 playwright(浏览器用用户自己的 Chrome)
- 流程: bat 检测 9222 → 无则(提示关 Chrome 后)以调试模式启动 → 用户登录 → python 抓取 → 剪贴板+ck.txt
- wukong 同思路参考: `D:\渗透\wukong\cdp_get_all_cookies.py`(asyncio+websockets, 9225 端口)
