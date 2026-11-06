## 参考
- `references/tiktok-signature-service-2026-08.md` — **签名服务探索（tiktok-signature + xgnarly.mjs 纯 node X-Gnarly + 外部重放 10201 结论 + IP 一致性原则）**，服务器采集的备选路线记录
- `scripts/proxy_bridge_srv.py` — **服务器端 socks5 认证 → 本地 HTTP CONNECT 代理桥（python 标准库）**，给签名服务/Chrome 用的无认证本地代理
- `references/collection-deep-dive-2026-08.md` — 深度诊断记录：游客/登录态触发差异、CDP getResponseBody 空体坑、App 协议(X-Gorgon)移植验证+App会话限制、tsx interop 坑、手动 CONNECT 隧道
- `references/tiktok-api-probe-2026-08.md` — 实测记录(SSR结构/接口参数/签名验证过程/400与空body的判别)
- `references/nextjs-14-browser-automation.md` — Next.js 14 集成 CDP/puppeteer-core 工程坑(node: 模块对象形式外部化/instrumentation edge 编译/tsx 调试/socks 包 external)
- `references/socks5-auth-bridge.md` — **带认证 SK5 的本地 HTTP CONNECT 桥完整实现(纯标准库)+ 验证方法 + PyInstaller 打包 Windows 交付工具的坑(onefile __file__/GBK emoji)**
- `scripts/抓tk_ck.py` — 用户侧 CDP 抓 Cookie 工具(智能版v3:内置代理+认证桥+自动启动Chrome+MessageBox弹窗);配套 bat 要点见 通道2
- `scripts/start-cdp-browser.cjs` — 服务端 headless 采集浏览器守护(纯 JS,pm2 托管,读 TIKTOK_CDP_BIN/PORT)
- `scripts/repro-bind-flow.js` — **绑定链路复现探针**(服务器上跑:桥+headless+注入CK,判别 profile/recommend/post 三接口;Orca 拦截排查用,2026-08-16 验证)

