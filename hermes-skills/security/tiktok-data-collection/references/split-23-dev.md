## 给用户看 dev 预览的技巧
- 用户"搞个dev我看看"时:dev server 起来后,用 `open_preview` 在预览面板打开页面让用户直接看,比截图更直观
- 登录态页面(账号管理页等)预览面板没有登录 cookie → 用 **CDP 注入会话**:`curl` 登录拿 set-cookie → 连 9222 调试 Chrome `Network.setCookie`(domain=localhost) → `Page.navigate` → `Page.captureScreenshot` 存 png → **MEDIA:路径直接发图**(用户能内联看图)
- 当前模型(deepseek)无原生 vision 且辅助视觉模型不支持 image_url → `vision_analyze` 会 400 失败,**不要依赖它验证截图,直接发图让用户看**,再让用户描述问题
