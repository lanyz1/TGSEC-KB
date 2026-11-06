## 四步法(顺序不能乱)
1. **拿合法 initData**:用 Telethon `RequestAppWebViewRequest` + `InputBotAppShortName`(短名≠bot 用户名!)取 `#tgWebAppData=`。后台只接受**单层 URL 编码**形态。
2. **复刻协议**:bundle 里找握手 —— X25519 ECDH → HKDF(salt 通常是**硬编码**的产品名)→ 32B 双用(AES-GCM key + HMAC key);请求头 `X-Session-Id/X-Timestamp/X-Nonce/X-Signature`。
3. **对拍定罪**:本地 Chrome 跑 bundle 原版 WebCrypto(`exportKey('pkcs8',…)` 导 X25519 私钥)与 Python 实现逐项比对,**8/8 全等后才可怀疑输入**。
4. **签名串长度/分隔符是最常见的真凶**:JS `[method,url,body,ts,nonce].join(\`\n\`)` 只用一个 LF。用 Python 文本模式 dump bundle 会把 LF 变成 `\r\n` **伪影**,必须重取线上字节核对,否则永久 `407xx`。

