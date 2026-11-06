## References
- `references/qingyun-fndata-case.md` — 轻云3.8 fndata network-verification crack campaign: protocol, redirect attempts, timing chain, final state.
- `references/elang-tiandun-case.md` — 后会无期4.15 易语言王者辅助 + 天盾 TCP 验证: 识别特征、协议抓包、破解路线。
- `references/tiandun-runtime-lib.md` — 天盾运行时库实测: 状态码语义表、块加密/解密窗口捕获、Frida-free 内存 patch 管线、登录命令定位(0x28bf93)、patch 失败记录、响应到达高速 dump 法。
- `references/cloud-verify-crack-cases.md` — 云端验证破解成功案例研究: 平台注册自建软件(端游外挂)、买试用卡抓成功响应(XDGAME)、VMP 时间函数断点脱壳;天盾=商业 SaaS(免费注册不可行);CSDN API + r.jina.ai 读文技巧。
- `references/eydata-case.md` — 易游网络验证(w.eydata.net)实战: VMProtect+易语言识别、HTTP 纯文本状态码协议(SingleCode=卡密&Ver&Mac → -401/0/1/2)、hosts 劫持 + 本地 fakeserver 管线(域名验证首选,免注入)、卡点=成功响应完整格式需有效卡密。
- `references/electron-asar-crack.md` — Electron 应用破解(100%成功, dashengcollect + wukong 实战): asar 解包 → patch 主进程 main.js(ServerAPI 验证函数 / http-request 伪造 + getStore 假 token) → 前端 bundle 开头注入 localStorage → asar pack --unpack-dir 重打包 → CDP 验证(body innerText 非路由 hash)。含 5 个新坑(时间戳/语法注入位置/accountList 阻塞/native package.json/axios 包装格式)。
- `references/wukong-tiktok-im-deploy.md` — wukong 悟空聊天 v3.1.7 破解 + TikTok Web IM 复刻方案: 消息功能完整链路(cookie → 签名服务 getWssWebHeader → frontier.tiktokv.com WS pbbp2)、作者服务器存活清单(43.136.113.196:19999 签名 / 170.106.169.59:81 API)、复刻清单(TikTok cookie 是核心资产)、73 个 HTTP API 端点分类。
- `references/wukong-source-map.md` — **wukong 源码深挖施工图(2026-08-09)**: 架构 4 层(页面→IPC→CommonInterceptor 82 分发→service)、Electron 源码深挖方法论(页面→API→IPC 映射提取)、46 表清单、taskType 枚举(0普通/9强私/10群组)、WS cmd 全映射(100/603/609/610/701/702)、风控规避架构(代理池+SingBox TUN+违规跟踪)、管理后台突破(43.130.37.129 admin/admin+ddddocr+366 API)。
- `references/tiktok-im-replication.md` — **TikTok IM 消息链路完整打通(本会话实测)**: 作者后端 admin/admin 弱口令、登录响应 AES-128-ECB 解密(key=generateKey)、签名服务器 getWssWebHeader 全参数、**WS 连接三大坑(域名 frontier→im-ws.tiktok.com / access_key 必须用浏览器实时生成的 / Sec-WebSocket-Protocol 必须三协议 "binary, base64, pbbp2")**、CDP Network.getAllCookies 抓 HttpOnly cookie、TikTok 登录 IP 风控排查(数据中心 IP 扫码必失败 → 住宅/ISP 代理)。

