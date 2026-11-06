---
name: webapp-api-crypto-reverse
description: "破解前端加密API协议(SM4/AES, webpack chunk逆向)。触发: 加密接口, data密文, SM4。"
---

# Web 前端加密 API 逆向(webpack chunk → 接口 → 对称加密破解)

对"前端把请求参数加密(SM4/AES + 动态密钥)"的 Web 应用,从 JS 逆向出完整可调用的加密协议。

## 适用场景
- 网页应用请求带 `?data=<base64/hex 密文>`、参数加密、国密 SM4/SM2、动态密钥(日期前缀)
- 已知前端框架为 Vue/React + webpack 打包(business-view/#/... 类 SPA)
- 目标:不依赖页面交互,直接用 Python 重放加密 API

## 方法论(验证过的流程)

### 1. 抓 webpack runtime(找 chunk 加载规则)
- 抓 SPA 入口 HTML(`/xxx-view/`),**内联 `<script>` = webpack runtime**
- runtime 里找:publicPath(`.p="..."`)+ chunk 列表(`h.e=function(e){...}`)
- **chunk URL 格式**:`publicPath + "js/" + chunk名 + "." + 版本号 + ".js"`(webpack 5 named chunks 带版本后缀,**不是 hash**;常见 404 原因是漏了版本号后缀,如 `.1787574513567.js`)
- 路由 chunk 在 app.js 里:搜 `{path:"/auction/xxx",component:...chunk-354c2e94...}` → 页面 chunk 名

### 2. 提取 API 模块(大 chunk)
- 业务接口集中在**一个 2MB+ 的巨型 chunk**(如 chunk-65b3177a)
- 提取:正则 `url\s*:\s*["'](/[a-zA-Z]+/[a-zA-Z]+[^"']*)["']` → 全部接口路径
- 搜关键词过滤:`pack|auction|notice|proj|bid` 等

### 3. 找请求封装模块(urlType → baseURL + 加密入口)
- 页面调用形如 `Object(o["Xx"])({...})`,API 函数定义形如 `Object(r["a"])({url:"/bidRoom/packTable",method:"get",urlType:"bidding",encryption:!0,params:t})`
- 封装模块(如 `b775:function`):**urlType 决定网关** —— `bidding→/business-proxy/business-bidding`、`oss→/business-proxy/business-oss`、默认 `/business-proxy/business`(多网关必须区分!)
- 加密分支:`e.encryption && (e.params={data:SM4(key, JSON.stringify(e.params))})`;响应解密 `SM4decrypt(key, e.data)`
- **密钥材料常量在封装模块顶部**:`var p="memberserver", b="$e9s20@2o4u^r2"`(p/b 是 key 组成部分)

### 4. 找加密实现模块(算法 + key 生成)
- 封装模块引用 `Object(m["d"])`/`Object(m["c"])` → 模块 ed08 之类,导出:日期函数、补齐函数、encrypt/decrypt
- **常见 key 生成**:`v = 日期(YYYYMMDD)`, `y = (v + 密钥串)[:16]` → **SM4 密钥 = 每日动态!**
- 算法确认:搜 `sm4encryptEcb = function(e,t){...}` → `sm4_crypt_ecb` + `padding`(PKCS7)+ `sm4_setkey`(标准 FK/CK)
- 输出格式:`base64js.fromByteArray` → **密文 base64**;输入 key 也要走 UTF-8/补齐

### 5. Python 重放
- 纯 Python SM4-ECB(标准 S 盒/FK/CK,PKCS7)约 60 行,先过国标测试向量:`key=0123456789abcdeffedcba9876543210, pt=同key, ct=681edf34d206965e86b3e94f536e4246`(不过向量 = 实现有 bug,先修再调接口!)
- 请求:`GET /business-proxy/business-bidding/bidRoom/packTable?data=<base64(SM4(JSON params))>`
- 响应:裸 base64(可能无 JSON 包装)→ base64 解码 → SM4 解密 → JSON
- **日期用目标业务时区(北京 UTC+8),不是服务器时区**;跨天 key 会变

## 陷阱
- **固定响应密文 = 请求没被服务器认可**(token 头格式/参数缺失),不是解密 key 问题;先检查 Authorization 头怎么生成(JS 里 `headers[k]=Object(a["a"])()` 的 token getter,可能不是裸 token)
- 先验证加密实现(测试向量)再怀疑 key
- 多个网关(baseURL)按 urlType 区分,调错网关 500
- 猜接口路径效率极低,一律抓 JS;静态 JS 404 时找 runtime 的版本号后缀
- GET 参数带 `r`(时间戳+随机)与业务参数一起加密

## 用户偏好(强制)
- **国内目标(95306 等)所有探测/调用必须走跳板机/主服 SSH 执行,严禁本机浏览器/本机直连**(用户多次强调「不要用本机,给你那么多跳板机要你干啥」);本机仅写脚本,执行全在主服
- 调用频率低频小批量,防 WAF

## 支持文件
- `references/95306-bidding.md` — 95306 竞价系统专属:数据平台表、selectSelfSellList status 码、接口清单、SM4 密钥材料、未完成项


---

## 外部库增量（2026-10-11 分享包）

## 分层码 · 密钥轮换 · 真明文取证(信封通关后的定位纪律)

- ★ **「信封已被接受」的唯一廉价铁证 = 响应体本身是密文且能被本地内嵌私钥解开**:服务端只对**解开过的**请求回加密响应(响应头带 `encrypt-key`) ⇒ 看到「HTTP 200 + 可解密的密文体」即信封层已过,此后失败**一律不是 crypto 问题**。(比「拿 permitAll 端点回业务文案」更快,且对任意路径自证)
- ★★★ **三层各有专属码,别用一个码解释三层**:`400 Invalid encrypted request` / 框架 `403 {timestamp,status,error,path}` = **信封层拒**;**密文体内 `code:401`(认证失败)= 票层缺**;密文体内 `code:200` = 真成功。**HTTP 状态码不承载分层信息**(200 里既能装 401 也能装成功) ⇒ 判读永远以**解密后的业务码**为准。见到密文内 401 就去搞票,别回头改 crypto/换密钥。
- ★★★ **本地公钥与 bundle 现役公钥不一致 = 已轮换 ⇒ 结论是换钥匙重打,不是改算法**:症状为「前几日还通、今天全失败且文案退回信封层」。判法:取 bundle 现役公钥(`setPublicKey(<常量>)` 的实参、或配置项 `VITE_GLOB_RSA_PUBLIC_KEY` 类字面量)与本地 key 文件**比 modulus**;替换后若响应从「框架默认错误页/明文错误」变为「加密响应体」= 轮换确认。换钥匙后仍失败才轮到查算法。
- ★ **RSA 常量提取的正则盲区**:512-bit SPKI 以 **`MFw`** 开头(2048-bit 才是 `MII…`);PKCS#8 私钥以 `MIIBVAIB`(512)开头。只 grep `MII|MIG` 会**静默漏掉短钥匙**,进而得出「bundle 里根本没公钥」的错误结论 —— 提取时连 `MFw|MFg|MEg|MA0` 一起覆盖。
- ★★ **加密前明文用钩子直接截,别猜载荷结构**:`JSON.stringify`(拦住即将被加密的 JSON)、`TextEncoder.encode`、`btoa`/`atob` 即可同时拿到**加密前真明文与解密后真明文**。实测常截到 `{}`(2 字节 → PKCS7 补齐 16 字节)⇒ 身份**不在载荷里**,一次砍掉整条「试各种 uid 序列化形态」的岔路。`crypto.subtle.*` 全程 0 事件 ⇒ 加密是纯 JS 实现(CryptoJS 类),与 WebCrypto 无关,别去钩 `importKey`。
- ★★ **身份载体四查消去法(定位「谁在证明我是谁」)**:① grep bundle 是否真带 `Authorization`(命中可能只在 **axios 库内部**的 accessor/Basic auth 字符串里 ⇒ 前端根本没带 token);② `Network.getCookies` 列该源全部 cookie + 钩 `withCredentials`(false/0 cookie ⇒ 非 cookie 承载);③ 设备/访客指纹头(缺它时服务端**静默丢 body**,症状伪装成契约错);④ 钩 `JSON.stringify` 看载荷明文。四项逐条消去后剩下的才是结论 —— **别凭「页面看着像登录后」断定有活会话可骑**。
- ★★ **「重放旧请求仍回 HTTP 200」不是活会话证据**:200 可能只是 HTTP 层正常,业务码藏在密文里(解密后 401)。判活跃会话**必须解密业务码**,否则会为一个已死的会话白烧整轮。
- ★★ **匿名面判定必须 GET + POST 双形态各打一遍**:拦截器里 `["DELETE","GET"]` 走 query+头、POST/PUT 走 body,是**两套独立白名单** ⇒ 只发 POST 会把「仅 GET 侧匿名」的端点误判成「需鉴权」,反之亦然。逐路径双形态各一发,比扫路径清单便宜。

## 前端加密 oracle：`window.goEncrypt/goDecrypt`（2026-08 Go WASM 实战）
- 全站 API 走 Go WASM AES-CBC（密钥嵌在 `/main.wasm`），但页面加载后 `window.goEncrypt` / `window.goDecrypt` **直接可调**
- 不用逆 WASM：无头 Chromium 打开登录页 → `typeof window.goEncrypt === 'function'` → 在页面 context 里加密/解密
- 自动化：CDP `Runtime.evaluate` 传 payload，取密文 → curl 发 → 回来再 evaluate 解密
- 同理适用于 `window.encrypt`、`window.jsEncrypt`、`window.__CRYPTO__`、`window.sm4`
