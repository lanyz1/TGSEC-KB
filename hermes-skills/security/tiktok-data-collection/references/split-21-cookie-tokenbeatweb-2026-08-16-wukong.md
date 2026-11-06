## ★Cookie 有效性验证 = 官方 tokenBeatWeb 协议(2026-08-16 实测,wukong 参考,最终方案)
- **为什么**:CDP 浏览器采集验证(打开页面查 SSR 数据)受 **headless 指纹**影响——TikTok 风控不给自动化浏览器登录态数据 → 页面无数据 → **有效 Cookie 被误判"已失效"**(用户"新抓的 CK 绑定报无效"的另一重要根因,与 Orca 拦截并列)。官方鉴权接口不受渲染影响
- **协议**(wukong `asar_extracted/electron/api/tiktokAPI.ts` tokenBeatWeb 方法,反编译参考):
  ```
  GET https://www.tiktok.com/passport/token/beat/web/?device_platform=web&aid=1459&scene=boot
  头: cookie=<完整cookie> + UA(Chrome Windows) + sec-ch-ua/sec-ch-ua-mobile/sec-ch-ua-platform
      + Origin: same-site + Sec-Fetch-Mode: cors + Sec-Fetch-Site: same-site + Pragma: no-cache
  响应 error_code===0(顶层或 data.error_code,注意个别是字符串 "0")= 登录态有效
  ```
- **无需浏览器渲染、无需签名算法(X-Gnarly)**——纯 HTTP,秒级、精准。本地实测:wukong 真实登录 Cookie + SK5 代理 → ok:true;香港服务器直连接口 200
- 服务器实现:`src/lib/tiktok/token-beat.ts`(手动 CONNECT 隧道 + socks5 走桥 + http 代理带 Proxy-Authorization,node 标准库零依赖)
- **绑定流程改造(bindAccount)**:① 先 tokenBeat 快验证 → 失败 400 明确报错(proxy 失败→"代理连接失败";否则"登录态已失效");② 通过 → CDP 采集 profile+videos **尽力而为**(catch 回退空数据,60s 兜底),**采集失败不再误判 Cookie 无效** → 绑定必成(tokenBeat 是唯一裁决)
- **工具端同步验证(v1.1.6+)**:抓取成功 → 本地 tokenBeat 验证(urllib 走桥,15s 超时)→ False 立即提示"登录态验证未通过,请确认已登录后重试"(不复制);True → "登录态有效,可绑定平台";None(网络失败)→ 复制但提示无法验证
- **★webpack 坑**:token-beat.ts 用 `node:net/tls/https` → next.config externals **必须加 `{ "node:tls": "commonjs node:tls" }`**(net/https 已有),否则生产 build 报 `Build failed because of webpack errors` + `Import trace: node:tls`。引入新 node 内置模块后先本地 `npm run build` 再部署
- **参考 wukong 更多协议**:`D:\渗透\wukong\asar_extracted\electron\api\tiktokAPI.ts`(2976 行)含 iOS tokenBeat(X-Gorgon 签名)、私信/IM protobuf、账号管理全协议——同类需求直接挖这个文件,比逆向 web 端快

