## 验证登录（dev）
- **⚠️ LanguageSync 客户端语言源 = localStorage 非 cookie（2026-08-06 S11 检查误判教训）**：`document.cookie='qavlixor-lang=zh;path=/'` 只影响 SSR 首屏，**不触发客户端 LanguageSync 翻译**——用 cookie 切语言后页面仍全英文，会误判"页面不跟随语言"（S11 入驻页差点误报 bug）。**真实验证路径 = 点击页面右上角 LanguageSwitcher 选目标语言**（写 localStorage + cookie + 触发 qavlixor-language-change 事件）。浏览器沙箱里直接 `localStorage.setItem('qavlixor-lang','zh')` 可能 SecurityError（Access denied）——就用真实切换器点击。双态验证流程：中文态截图 → LanguageSwitcher 切英文 → 查英文 → 切回中文。
- 浏览器会话登录态每次导航易丢 → 用 fetch 直接调 `POST /api/auth/login`（JSON email/password）保 cookie，比表单点击稳
- 演示账号 <EMAIL-REDACTED>（值不入 memory，见 HANDOFF 文档）
- **用户催进度时**：探针一次合并多量测；登录 fetch 直连；dev 卡死先查 3000/3001 端口再重启（见下节），别反复空转

