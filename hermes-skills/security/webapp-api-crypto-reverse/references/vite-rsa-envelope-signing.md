# Vite 打包 + RSA+AES 信封 + 签名头逆向(2026 QQLink/KbitPay 实战)

webpack+SM4 之外的第二个常见变体: Vite 打包前端 + RSA+AES 信封 + HMAC 签名头。完整方法论, 前端 JS 是协议说明书, 别逆向二进制猜 key。

## 1. Vite 打包 chunk 提取(与 webpack 不同)

- 入口 `index.html` → `assets/js/index-*.js`(Vite)
- chunk 引用 = `` import(`./xxx.js`) `` + `__vite__mapDeps` 数组, 真实路径 = `"js/xxx.js"`(带 `js/` 前缀)
- **grep 必坑**: `'"[A-Za-z0-9._-]+\.js"'` 抓 Vite chunk 0 命中; 正确 = 抓 `__vite__mapDeps` 里的 `"js/<name>.<hash>.js"`, 下载 URL = `https://host/js/<name>.<hash>.js`(js/ 前缀不是 assets/)
- 模板字面量 URL(`url:\`/Xxx/Yyy\``)在 shell 双引号里 grep 因反引号转义失败 → 单引号模式或 python 搜
- 163 chunks → grep 业务前缀(如 `webv1/Admin*`)→ 端点全量

## 2. RSA+AES 信封 + 签名(前端 http-crypto 模块逐字还原)

```javascript
// AES-CBC: 32B 随机 key, IV = key 前 16B, PKCS7, 输出 b64
// RSA 包 key: JsEncrypt PKCS1v15(hex(key 字符串), pubKey) → b64 → urlencode
// 封装: {data: AES密文.b64.urlencode, aes_key: RSA密文.b64.urlencode}
// 签名: X-Signature = HMAC-SHA256(secret, 字段值排序 + "&" + timestamp + "&" + nonce) hex
// 头: X-Api-Key / X-Timestamp / X-Nonce / X-Signature
```

**关键(全踩过的坑)**:
- **PKCS1v15 不是 OAEP**(试 OAEP 必失败)
- body 直接 = `{data, aes_key}`; 包一层 `{"userInfo": json.dumps({data,aes_key})}` 必回 `Invalid AES key or data`
- **签名对象 = 加密后的 body**(先加密再签名), 不是明文
- GET 请求签名对象 = **query params**(不是 body)
- 注册用第三方应用 `X-Api-Key`(apiKey)+ apiSecret 签名; 登录后业务接口改用**返回的 secret_key** + Bearer
- header 大小写敏感: `X-Api-Key` 大写才认, 全小写 `x-api-key` 不认
- 服务端 `Invalid AES key or data` = key 为空/请求没被识别(缺 header 或格式错), 不是猜 key 的提示

## 3. JWT 伪造 → 任意用户

- 注册拿 token → base64 解码 payload 看结构(HS256 + claims 字段名)
- 若 signing-key 泄露(GVA getSystemConfig / 配置)/ 短弱密钥(`J05KlCa` 7字节) → 伪造任意 userId token
- 注意: 签名密钥 ≠ 业务 secretKey; payload 里 userSecret 必须是目标用户**当前** secretKey
- 实时 secretKey 优先查 Redis hash(user_signature_secret, uid→64hex), DB 值可能过期

## 4. 管理台 IP 白名单绕过(ASP.NET Core 平台)

- **白名单中间件只挂 POST 路由**: GET 接口全部绕过(返回 405 = 路由存在但方法错 = 白名单已过, 不是 403)
- **非业务前缀接口绕过**: `/PayApp/*` `/MchAccount/*` `/WalletDeposit/*` 等不挂白名单
- `GET /PayApp/GetAppKey?id=N` → 商户 AppKey/AppSecret 明文
- `GET /Login/CheckLastLogin?email=x` → 账户枚举(ResData true/false)
- POST 业务接口仍需 RSA+AES 信封(4044 = 缺加密协议)
- 框架识别: ASP.NET Core 错误含 `traceId`/RFC 9110 引用; GoFrame 是 `{ErrCode, ErrMsg}`

## 5. 资金盘定性信号

- 内账(DB 余额) vs 链上真实资金严重脱节 = 资金盘
- 出金链路: 用户提现 → 扣内账 → 审核 → 平台以商户身份调代付 API → 热钱包链上打币 → 回调
- 热钱包抽空 + 大量卡单(state=3 无 tx)+ 配置指向测试线 = "提不出钱"是资金结构问题, 不是代码漏洞
