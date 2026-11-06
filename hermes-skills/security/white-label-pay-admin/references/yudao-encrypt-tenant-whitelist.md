# 芋道 yudao ApiEncrypt + 租户白名单（白标支付后台）

Session pattern from worldxpp/lucky* stack (2026-09).

## Transport crypto

- Header: `encrypt-key` (RSA-encrypted AES key material)
- Body: Base64(AES-ECB-PKCS7(plaintext))
- Frontend embeds **RSA private key** used to decrypt `encrypt-key` on responses, and a **public key** to encrypt request keys.
- AES key material: 32 random alnum chars → UTF-8 bytes → Base64 string → RSA encrypt that Base64 string into `encrypt-key`; AES uses the raw 32-byte UTF-8 key (after Base64-decode of the RSA plaintext).

Decrypt sketch:

```python
# RSA decrypt encrypt-key -> base64(aes_key_bytes)
# AES-ECB unpad decrypt body -> JSON
```

Password field (LoginForm remember-me) uses a **separate 512-bit RSA** public key in JS — not the transport key.

## Content-Type fork (CRITICAL)

| Request | Server behavior | Typical result |
|---------|-----------------|----------------|
| `Content-Type: text/plain` + AES ciphertext body | Decrypt path | Often `{"code":500,"msg":"系统异常"}` |
| `application/json` + plaintext short password | **Skips body decrypt**; validates fields | `400` if password length not 4–16; else **`403 没有访问权限`** |

`403` here is **IP allowlist**, not wrong password. X-Forwarded-For / X-Real-IP / CF-Connecting-IP / True-Client-IP usually do nothing.

## Tenant discovery

```http
GET /admin-api/system/tenant/get-id-by-name?name=Lucky1Pay
```

Often works unauthenticated (encrypted response). `get-by-website` frequently returns null even for live brands.

Observed IDs (lucky1pay ALB):

- Lucky1Pay / lucky1pay → 5
- AaaPay / Aaapay / AAAPay → 9
- Xepay / XePay / xepay → 11

Send `tenant-id: <id>` on subsequent calls.

## Post-auth gold

```http
GET  /admin-api/system/tenant/white-ips?id=<tenantId>
PUT  /admin-api/system/tenant/white-ips   # body: {id, whiteIps[], googleCode}
```

Whitelist entries may include origin / ops egress IPs useful for CDN origin tracing.

## Login prerequisites (from LoginForm)

- `captchaEnable: "false"` common — skip slide captcha unless flipped true
- `tenantEnable: "true"` — resolve tenant name → id before login
- Host special-case example: `lucky1pay.com` rewritten to `admin.lucky1pay.com` then `get-by-website` / name fill
- Optional `googleCode` (GA); empty often allowed

## Ops note

Tor/datacenter exits get 403 on plaintext login. Need residential / allowlisted egress (or pivot through an already-trusted sibling host) before password spraying is meaningful.
