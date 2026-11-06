## ★tiktok-signature 签名服务探索（2026-08-19，部分可行，未最终闭环）

- **资源**：npm `tiktok-signature`（v4.3.6）——webmssdk 完整 SDK（`javascript/webmssdk_5.1.3.js` 等 3 个版本）+ **`xgnarly.mjs`（220 行纯 node X-Gnarly 算法，零浏览器依赖，ChaCha20 + 自定义 base64）** + 签名服务（server.mjs，puppeteer-extra stealth + Safari macOS UA + MacIntel platform + 1920x1080 viewport）
- **xgnarly.mjs 用法**：`encode(queryString, body, userAgent)` → X-Gnarly 头值；`fields` 含 `md5(queryString)/md5(body)/md5(UA)/ts/sdkVersion`（sdkVersion 默认 "1.0.0.368"，字段9 固定 "5.1.3-ZTCA"）——**可纯 node 生成 X-Gnarly（不访问 TikTok、无指纹检测）**，已拷入项目 `src/lib/tiktok/xgnarly.mjs`
- **部署实测**：服务器 `/srv/tsig`（server.mjs + xgnarly.mjs + javascript/webmssdk_*.js + puppeteer-extra）→ `node server.mjs` → `/health` OK（initMethod: local-sdk, hasAcrawler:true, 捕获 6 cookies）——**webmssdk 本地注入成功，浏览器无需访问 TikTok 页面也能生成签名**
- **★外部重放无效（实测确认）**：`POST /signature` 返回签名 URL（1153 字符，含 X-Gnarly/msToken）→ curl 外部重放（同 IP）→ **HTTP 400 statusCode 10201**——签名绑定浏览器会话上下文，外部重放被 TikTok 拒绝（与 memory 既有结论一致）
- **★IP 一致性原则**：香港服务器 IP 会话下 `/fetch` 也 10201（IP 层被风控）；签名服务加 `PROXY_ENABLED=true PROXY_HOST=127.0.0.1:8888`（本地桥 → 用户代理）后 `/fetch` 返回 `httpStatus:200`（过了风控）但 `data:null`（浏览器内 fetch 响应仍空）——**最后一步未闭环**（浏览器会话签名 fetch 的响应仍空，可能参数/会话上下文问题）
- **经验教训**：① secUid 从 SSR 实时解析拿**完整值**（测试截断版导致 10201 误判）；② 服务器起 socks5 认证桥用 python 脚本（`scripts/proxy_bridge_srv.py`，socks5 握手 + 双向 pipe）；③ 签名服务的浏览器会话 IP 必须 = 外部请求 IP

