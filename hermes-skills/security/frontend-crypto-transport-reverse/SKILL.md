---
name: frontend-crypto-transport-reverse
description: "Use when 前端 crypto-js/jsencrypt 加密传输需逆向解密复现。"
---

# 前端加密传输逆向（crypto-js + jsencrypt）

灰产钱包/资金盘（USDT 充提、话费、虚拟卡、直播游戏充值）、博彩盘、TG Mini App 前端常用这套「加密传输」伪装安全。核心结论：**前端硬编码的密钥 = 加密形同虚设**，全部可逆向。

## 识别特征
- 首页 HTML 引 `crypto-js-*.js` + `jsencrypt-*.js`（Vite/Vue 打包，`<script type="module">`）。
- 请求头带 `encrypt-key`，GET 参数带 `encryptParams`，POST body 是 base64 密文。
- 响应带 `encrypt-key` header，body 是 AES 密文的 base64。

## 加密机制（可完全逆向）
前端 `index-*.js` 里常**硬编码 RSA 私钥**（`setPrivateKey($e)` 的 `$e` 就是完整私钥 PEM）：
- 每次请求生成随机 32B AES key → `AES-ECB(PKCS7)` 加密参数/body（`y.mode.ECB`）。
- `encrypt-key` header = RSA 公钥加密 base64(AES key)。
- 响应：`encrypt-key` header = RSA 加密的响应 key，body = AES 密文的 base64。

**RSA 私钥在前端 = 响应加密完全失效**，攻击者可解任何加密响应（高危，直接写报告）。

## Python 复现（用 cryptography，不用 pycryptodome）
```python
from cryptography.hazmat.primitives.asymmetric import padding as apad, serialization
from cryptography.hazmat.primitives import padding as spad
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
pub = serialization.load_der_public_key(base64.b64decode(PUB_B64))
priv = serialization.load_der_private_key(base64.b64decode(PRIV_B64), password=None)
# 加密请求：AES ECB 加密 json.dumps(...) → base64；RSA 公钥加密 base64(aeskey) → encrypt-key header
# 解密响应：RSA 私钥解密 encrypt-key header → base64 解码 → AES key；AES ECB 解密 body
# jsencrypt 默认 PKCS#1 v1.5（apad.PKCS1v15）；AES 用 ECB + PKCS7
```

## 双重 base64 坑（必踩）
响应 body 文本**本身是密文的 base64 字符串**（后端返回的是 `AES.encrypt(...).toString()` 的 base64 文本），不是密文二进制。解密顺序：
1. 原始 body（文本）→ `base64.b64decode` → 真正的密文字节。
2. RSA 私钥解密 `encrypt-key` header → base64 解码 → AES key（32B）。
3. AES-ECB 解密密文字节 → 明文 JSON。

从 fetch 的 `arrayBuffer` 再 `btoa` 一层会双重 base64，AES 解出乱码 / `Invalid padding bytes` 报错——先 `base64.b64decode(body_text)` 再 AES。

## 认证硬边界（打不穿别硬耗）
- 后端常见 Spring Boot 全局认证拦截器，白名单只有「时间戳」+「checkInitData」两个，其余全 401（响应形如 `{"code":401,"认证失败"}`）。
- `checkInitData` 用 TG bot token 的 HMAC-SHA256 严格验签 → 伪造 initData 必返回「签名验证失败」。
- 突破认证必须拿 bot token（伪造签名）或有效 initData（重放）；**bot token 不在前端**，全局 grep `[0-9]{8,12}:[A-Za-z0-9_-]{30,45}` 确认。
- Spring Boot actuator 可探测（`/actuator/health` 等），但 `/actuator/env` 常被 WAF 单独拦（405），其余端点 403——源站 IP 走阿里云盾源站隐藏时难挖。
