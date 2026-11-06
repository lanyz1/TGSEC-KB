---
name: offline-api-signer-replication
description: "签名挡路(x-api 类): WASM/JS 签名器搬进 Node 离线复现打 API。"
version: 1.0.0
license: MIT
tags: [签名, 签名算法, 接口签名, 签名算不出来, x-api, WASM签名, 离线复现, node复现, sign]

---

# Offline API Signer Replication (WASM/JS → Node)

授权测试中 API 带签名头/签名字段、自动化被「不会算签名」挡住时：**签名怎么算不用全懂——把执行体（wasm/JS 模块）搬出来直接跑**，再测服务端校验强度。盘口类配套详卡 `gambling-api-crypto-reversal`（用户自有）；本卡=通用方法与执行细节。

## 何时用
- 请求头有 `x-api-xxx`/sign/signature/encrypt，值每次变化（掺时间/随机）
- 签名器在 WASM、混淆 JS、Next.js/webpack 懒加载 chunk 里
- 想规模化（IDOR/fuzz/枚举）但签名挡住了脚本

## 工作流
1. **拿执行体（全量 chunk）**：Next.js 首页 grep `/_next/static/chunks/*.js`，**再**解析 webpack runtime 全映射 `(\d+)===e\?"([^"]+)"`，下载所有懒加载 chunk（签名器常在小 chunk + 伴随 .wasm，只抓首页必漏）。**懒加载 chunk 的 URL 是 `/_next/static/chunks/<id>.<hash>.js`（点号），wasm 在 `/_next/static/wasm/<hash>.wasm`；写成 `chunks/<id>-<hash>.js` 会 404**，别被自己的拼法骗过去。Vite/Nuxt 类抓全 /assets/。grep 大小写不敏感（JS 里 X-API-XXX 大写、HTTP/2 抓包小写）。找 interceptor/headers 组装层。
2. **定位输入**：常见=URL 前两段当“频道”（`url.match(/\/\w+\/\w+/).shift()` → /site/api）；合法输入常是**精确白名单**（频道串 + env ∈ prod/dev/release）。
3. **wasm-bindgen → Node 直跑（旗舰）**：先看 `WebAssembly.Module.imports/exports`；imports 常仅 now/random/floor/throw（Date.now/Math.random/Math.floor/throw 替身）。调用约定：`sign(sp, p1,len1, p2,len2)`；`sp=__wbindgen_add_to_stack_pointer(-16)`；字符串 malloc+手拷；返回读栈槽 Int32Array[sp/4],[sp/4+1]；free 后 add_to_stack_pointer(16)。内存增长 detach 视图→每次重建。模板：`templates/wasm_bindgen_sign_runner.js`。**trap 诊断**：`unreachable` 且没有任何 import 被调用 = 输入被拒（换精确合法值，别怀疑绑定代码）。
4. **规模化**：Node `--loop` 常驻签名器 + Python subprocess 逐请求现签。**签之前连调两次比对值**：不同 = 掺了 now/random（真实案例 `/act/api` 两次结果不同），**绝不缓存签名**。有的频道不在白名单：浏览器发字面 `"undefined"` 服务端照收——复刻降级逻辑。空 body POST 必带 `Content-Length: 0`（nginx 否则 411）。
5. ★ **校验强度矩阵（必测，直接写报告）**：垃圾值/缺头（是否真校验）/ 旧签名重放（时窗）/ 新签名（基线）/ 跨频道（A 签名打 B 路径）/ 跨账号。结论叙事：无逐请求绑定、无短时窗、跨频道放行 = 一个签名值≈全站通行证。
6. **token 链**：localStorage/token AES-CBC 常量 key/iv 解密复刻；token 头变换（`Base64(Hex(tok))`→AES-CBC，≥N 字符用明文否则原样）；JWT 类接口直接签发下游票。

### JS/混淆签名器变体（非 wasm，obfuscator.io 类）
- **契约先定位**：SPA 的 `js/services/*.js`、`js/core/*.js` 里搜 `fetch(`、`X-`、`generate` —— 拿准**字段名、位置（query 还是 header）、签名入参**。踩过的坑：gofile 的 `wt` 走 `X-Website-Token` **头**，且签的是**账号 token** 而非内容 ID——入参猜错只会得到 401 / `error-notPremium`。
- **真身在 `*.obf.js` 薄壳后面**：不要静态还原，`vm.createContext` 里 shim `navigator{userAgent,language}`、`window/self`、`atob/btoa`、`TextEncoder`、`crypto.webcrypto`，`runInContext` 后从 ctx 取导出函数直接调。
- **时间桶 + 服务端轮换密钥**（gofile=14400s）：过期就重拉最新 obf 产物重算，别缓存旧签名器。
- **验收看错误码阶梯**：401 → 业务错误 → `status:ok`，每层变化都是一次对齐确认。

## Pitfalls
- wasm trap 先怀疑输入值，不怀疑自己的绑定（DEBUG stub 看 import 调用序列）
- 别假设能长期重放：密钥轮换/时窗上线后要能现场重新签（wasm 方案自愈，纯重放会死）
- 别只抓首页 chunk；敏感值落盘看（显示层可能脱敏）

## Files
- `references/nextjs-wasm-signer-offline.md` — 完整案例解剖（zm1s8x/开云：chunk 挖掘、Node 跑 wasm、校验矩阵、密钥、离线客户端）
- `templates/wasm_bindgen_sign_runner.js` — Node 直跑 wasm-bindgen 签名模块模板
- `references/gofile-wt-signer-2026.md` — gofile 2026 取件：wt=SHA256(账号token/UA/lang/14400s桶) 进 `X-Website-Token` 头；分享 gate 状态解码（canAccess/public/password/expire）