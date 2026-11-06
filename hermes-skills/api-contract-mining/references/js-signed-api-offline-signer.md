# 离线复现前端签名（Node vm）通用套路

触发：API 要求浏览器端生成的签名字段/头（wt、sign、nonce、X-Custom），裸调被 401/403/业务错误拒绝。

1. **先定位契约**：在 SPA 的 `js/services/*.js`、`js/core/*.js`（或 webpack chunk）里搜 `fetch(`、`X-`、`generate`、`sign`——拿准**字段名、位置（query 还是 header）、签名入参**。别猜：gofile 的坑就是「签的是账号 token 而非内容 ID」且「走 `X-Website-Token` 头而非 query 参数」。
2. **找生成器实现**：`core/<name>.js` 往往只是薄壳，真身在 `*.obf.js`（obfuscator.io）。不要静态还原，直接执行。
3. **Node vm 执行**：`vm.createContext` 里 shim `navigator{userAgent,language}`、`window/self`、`atob/btoa`、`TextEncoder`、`crypto.webcrypto`，`runInContext(code)` 后从 ctx 取导出函数。混淆代码常探测 `document`/`location`，缺什么补什么，报错即提示。
4. **用错误变化验收**：401 → 业务错误 → `status:ok`，每变一次就说明签名对齐了一层；不同错误码就是分步探针。
5. **保鲜**：这类签名常含时间桶 + 服务端轮换密钥，过期就重跑生成器（重新拉最新 obf 产物）。

案例：gofile 2026 取件（`wt = generateWT(账号token)` → `X-Website-Token` 头）——完整协议见 bulk-data-delivery/references/gofile-receive-2026.md（用户自有技能，只读引用）。