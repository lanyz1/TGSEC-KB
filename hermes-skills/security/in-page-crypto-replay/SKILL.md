---
name: in-page-crypto-replay
description: "Use when frontend-encrypted APIs block scripted replay."
version: 1.0.0
license: MIT
---
# In-Page Crypto Replay

前端加密网关（AES+RSA+HMAC 信封、签名头）被 WAF 按 TLS 指纹拦死时的通用解法：
**不要在外围重放，钻进页面里重放。**

与 `offline-api-signer-replication`（离线 Node 复现签名器）互补：离线复现解决「算不出签名」，
本卡解决「签名算对了但请求还是 403/405」。判定顺序见下。

## Trigger
- bundle 里有统一加密函数（AES + RSA + HMAC 组合），请求体是 `{k,b}` / `{data,sign}` 之类信封
- Python 复现加密后仍然 403/405/挑战页
- requests / curl / curl_cffi 三件套全被挡，但浏览器里一切正常
- 密钥 grep 不到（运行时注入 `env`、服务端下发）

## 判层：先分清协议错还是 WAF 错
一条 CTRL 定生死 —— 拿页面**自动发**的那个接口当基线：

| 现象 | 结论 |
|---|---|
| CTRL 200，业务接口 4xx | 协议/参数问题，继续调加密与字段 |
| CTRL 403 `Just a moment...` | Cloudflare clearance 失效（IP 级或 UA/TLS 绑定） |
| CTRL 405 `Human Verification` + `window.gokuProps` | AWS WAF Bot Control |
| CTRL 200 但业务接口 405 | 该路径被单独按频率封了 |

**没有 CTRL 就不要调协议** —— 否则把 WAF 拦截当成签名写错，能白烧几小时。

## 1. 从 bundle 还原协议
找统一 request 封装（`request({url, data, secure, skipEncryption})`）和它的加密函数，逐项抄下：
时间戳字段与精度、nonce 生成法、明/密文字段名、密钥是静态常量还是运行时注入、哪些 header 参与签名。

**关键语义**：`secure:false` 通常只表示「body 不加密」，**签名头照样必带**。
裸 body 打过去返回 `400 Invalid ... Signature` 并不代表没破 —— 那是「签名是唯一门槛」的铁证。

## 2. 密钥不在静态文件 → hook crypto.subtle
静态 grep 不到密钥时别猜，hook 后 reload，让页面自己的加密请求把材料交出来：

```js
// Page.addScriptToEvaluateOnNewDocument，必须早于 bundle 执行，然后 Page.reload
const o = crypto.subtle, cap = window.__KC = [];
for (const m of ["importKey","generateKey","encrypt","decrypt","sign"]) {
  const f = o[m].bind(o);
  o[m] = async (...a) => {
    try { cap.push({m, raw: a.slice(0,2).map(x =>
      x instanceof ArrayBuffer ? [...new Uint8Array(x)] :
      x?.buffer ? [...new Uint8Array(x.buffer)] :
      (typeof x === "string" ? x : String(x)))}); } catch(e){}
    return f(...a);
  };
}
```

- `importKey(raw, …)` → HMAC/SHA 密钥明文
- `importKey(spki, …)` → RSA 公钥 DER（base64 后即 PEM body）
- `generateKey` + `exportKey("raw")` → AES key；`encrypt` 的 iv 与明文一并落库
- 同时 hook `fetch` / `XMLHttpRequest.open` 抓 header（`x-t/x-n/x-s/x-e`、`fp`、`fpPlus`）与明文 body

## 3. 页面内重放（真正的 WAF 绕过）

| 方式 | 典型结果 |
|---|---|
| Python requests + 正确签名 | 405 `Human Verification`（AWS WAF 按 TLS 指纹） |
| curl_cffi `impersonate=chrome131` | 403 `Just a moment...`（cf_clearance 绑 UA+TLS，版本不匹配） |
| 页面内 fetch + Web Crypto 自行加密 | 200，稳定 |

用模板 `templates/inpage_crypto_client.js`：注入后 `window.__HG.post(path, obj)`，
靠浏览器自己的 TLS 指纹 + cookie 发请求。**封装成带重连的客户端类**，页面上下文一丢就自动重建 ——
裸写一次性脚本会在第二轮全部返回 None。

**PEM 坑**：`atob` 不接受换行/头尾。取 `-----BEGIN…-----END-----` 之间的 body 后 `replace(/\s+/g,"")`，
或构建阶段就抽成单行 base64 再注入，否则 `atob … not correctly encoded`。

## 4. 字段与路径 oracle（别 fuzz，用报错逼）
- **路径存在性**：不存在的路径常回统一 `Unknown Error`／包装 404；回业务字段错 = 存在。
  先打一个乱码路径当对照组，否则把「路径不对」误判成「参数不对」。
- **字段名 oracle**：`xxx must not be empty` / `must not be null` 逐个逼出必填项；
  `must not contain spaces or special characters` 直接泄露正则规则。链式补字段，一轮挖完 payload。
- **前缀分域**：`/svc/prv/public/…` 与 `/svc/ply/public/…` 可能是**两套服务**（OTP/会话不共享）。
  先把 bundle 里的前缀常量挖出来再拼；发码与校验接口务必确认前缀一致。
- **类型混淆**：邀请码/推荐码 `"0"`、`"null"` 常直接过；`otpCode` 空串与缺失走不同分支
  （后端用 `== null` 而非 `isBlank`）—— 枚举 `"" / "0" / " " / 缺失` 四种即可定位。

## Pitfalls
- 高频请求会把 IP 打成硬封禁（CF 连 turnstile iframe 都不返回）→ **停手**，起守护轮询 CTRL 等冷却，别加深。
- 无头/坐标点击常失效：`.click()` 非 trusted，坐标容易打到导航栏同名按钮把弹窗关掉。
  用 `form.requestSubmit()` 或 `button[form="…"]` 触发 React onSubmit，再靠 hook 抓真实请求。
- 多 tab 弹窗（Mobile/Email OTP）切换用 JS 原生 `.click()` 触发合成事件，比鼠标坐标稳。
- 页面内注入代码里千万别带多行 PEM，注入器常按单行处理。
- 请求封装里 `skipEncryption:true` 的接口是真明文（带签名）；别把全部 `/api/` 都当成加密的。

## Files
- `templates/inpage_crypto_client.js` — 可注入的加密客户端骨架（Web Crypto 信封 + fetch + 自愈）。
- `references/envelope-replay-hengongbet.md` — 实战配方：AES-GCM + RSA-OAEP + HMAC-SHA512 信封、字段 oracle 全链、OTP key 分域坑。
