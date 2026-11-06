# TikTok 采集深度诊断（2026-08-19 会话记录）

本文件记录"应用 wukong 协议仍采不到作品"完整排查链的实测证据，供未来同类诊断对照。

## 1. 诊断顺序（先排除 IP，再排除浏览器，最后才怀疑协议）

```
tokenBeat 验证（登录态好？）→ 页面渲染（标题/用户信息？）
→ curl 对照（同 IP 纯 HTTP 有没有数据？）
→ 有数据 = IP 干净 → 问题在浏览器侧（JS 反爬/自动化指纹）
→ 无数据 = IP 降级（数据中心 IP）→ 换住宅代理
```

## 2. IP 信誉判定（两查一验）

```bash
# 权威类型检测（走同一代理）
curl --socks5-hostname 'user:pass@host:port' 'http://ip-api.com/json/?fields=query,isp,org,as,proxy,hosting,country,city'
# → hosting:false, proxy:false = 非机房非代理标记（用户 SK5 199.239.16.12 NTT America 实测干净）

# 行为验证（最关键）：同代理 curl @handle
curl --socks5-hostname 'user:pass@host:port' -H 'User-Agent: <Chrome Windows>' 'https://www.tiktok.com/@tiktok' -o page.html
wc -c page.html          # ≥200KB = 有数据（实测 368KB）；<15KB + captcha = 降级（香港机房 12KB）
grep -oE '"videoCount":[0-9]+' page.html   # 有值 = IP 干净
```

ipinfo.io 免费版 `type` 字段常缺，用 ip-api.com 更全。

## 3. SSR 数据结构实测（2026-08）

- 路径：`__DEFAULT_SCOPE__.webapp.user-detail.userInfo.{user,stats,itemList}`
- `user`：id/uniqueId/nickname/avatarLarger/avatarMedium/secUid/privateAccount/verified/signature
- `stats`：followerCount/videoCount/heartCount/followingCount（**作品列表不在这**）
- **`itemList` 永远是空数组**（即使 @tiktok 1491 作品）——作品列表要走懒加载 API
- HTML 里的 `"videoCount":1491` 是 stats 统计，不是作品数据

## 4. 游客 vs 登录态（作品请求触发条件）

| 模式 | 账号页滚动 | item_list 请求 |
|---|---|---|
| 游客（不注入 cookie）| ✅ 触发原生请求（带 secUid）| 200 + hasMore:true + itemList 完整 |
| 注入 cookie（登录态）| ❌ 不触发 | 手动 fetch 简参 = 200 空 body |

- 原生 URL 参数几十个（WebIdLastTime/aid/app_language/browser_language/browser_name/browser_version/browser_online/browser_platform/channel/cookie_enabled/device_id/device_platform/focus_state/from_page/history_len/is_fullscreen/is_page_visible/os/priority_region/region/screen_height/screen_width/tz_name/webcast_language/msToken/...）
- 手动 fetch 简参（uniqueId/secUid/count/cursor/aid）→ 200 空 body；**要复刻必须抄完整 URL 模板**

## 5. CDP 取响应体坑（未闭环）

- `Network.responseReceived` 捕获 item_list：status 200、`encodedDataLength` 1147 字节
- `Network.getResponseBody` 返回**空**（即使 responseReceived 时立即异步取、maxTotalBufferSize 100MB）
- 备选方向（未验证）：`Fetch.enable` requestPaused 拦截、或 responseReceived 后 50-100ms 内同步取
- **教训：encodedDataLength>0 但 getResponseBody 空 ≠ 响应真空，是 CDP 缓冲问题**

## 6. App 协议（X-Gorgon）移植验证

- 算法文件：`D:\渗透\wukong\asar_extracted\electron\algorithm\xGorgon8404.ts`（312 行，纯 TS + crypto，可整体拷入项目）
- 签名：`XGorgon8404.stringToMD5(params)` → `XGorgon8404.XGorgon84MD5(paramMd5, '', cookieMd5, null)` → {X-Gorgon, X-Khronos}
- 设备参数样例（wukong authAPI.ts:244 注释有完整 URL）：
  ```
  device_id=7578180034545813048 iid=7578180620715788044
  openudid=b6c9f664a3d13800d372c58795b34d4fe105462a
  cdid=0c0d1c9c-2b14-4b36-9b3c-7b7a1f2e3d4c
  ```
- 请求：`https://api16-normal-c-useast2a.tiktokv.com/passport/token/beat/v2/?<设备参数>&scene=boot` + X-Gorgon/X-Khronos 头
- 实测结果：**返回业务错误 `{"data":{"error_code":401,"error_name":"session_expired"}}`** = 签名+设备通过，但 web cookie 无 App 会话 → 401
- **结论：web cookie 不能用于 App 协议；aweme/v1/aweme/post 用 web cookie = 200 空 body。App 协议移植只对能拿到 App 会话的场景有意义**

## 7. 工具/脚本坑

### tsx ESM/CJS interop（本会话 3 次踩坑）
- `npx tsx -e "import ..."` 顶层 await 静默失败（无输出）；`import { named } from "./x.ts"` 报 "does not provide an export named"
- 解法：写 `.mts` 文件 + async main() + `const m = await import(...); const fn = m.named ?? m.default?.named`
- 项目 tsconfig module=esnext 但 package.json 无 type:module → tsx 按 CJS 转译导致 interop 混乱

### token-beat.ts 手动 CONNECT 隧道（node 标准库）
- `parseProxyUrl` + `startSocksBridge(host, port, user, pass)` → CONNECT host:443 → tls.connect({socket}) → https.request({createConnection})
- node http.request 走 CONNECT 隧道报 "Parse Error: Data after Connection: close"——**别用 node http/https request 复用隧道 socket，手动 sock.write HTTP/1.1 请求 + 手解析响应**（content-length 分帧）

## 8. 绑定流程最终架构（tokenBeat 裁决）

```
绑定 = ① tokenBeat 官方验证（秒级，error_code===0 = 有效）→ 失败 400 明确报错
       ② 通过 → CDP/HTTP 采集资料（尽力而为，失败不判无效）
       ③ 作品采集：游客 CDP 监听原生 item_list（方案验证中）
```
