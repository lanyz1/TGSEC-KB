## 6. 挑战值/随机数往往在 cookie,不在响应体
- 端点索要 `requestNo` / `nonce` / `captchaId` 而响应体里找不到该字段 ⇒ 读 `set-cookie`。
- 常见形态:`X-nonce=<uuid>` + `X-nonce.sig=<HMAC>` 签名 cookie 对(例:`sig-captcha-nonce` / `.sig`)。把值原样回填为请求参数即通过 —— 这是服务端签发的,无需你计算。

