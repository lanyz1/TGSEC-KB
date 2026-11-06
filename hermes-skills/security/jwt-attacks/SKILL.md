---
name: jwt-attacks
description: "JWT 攻击家族: alg混淆/弱密钥/kid-jku注入/IDP令牌签名缺验。触发: jwt, jose, jwt none, 令牌伪造。"
tags: [active_session]
---

# JWT 攻击家族(JWT Attacks)

核心公式:**签名校验点 × 身份来源 × 令牌作用域**。三类打法:①签名没验/验错 → 自己签;②签名验了但密钥可猜/可换 → 密钥攻击;③签名没问题但 claim 语义没查 → 伪造身份字段。目标是任意用户/管理员会话。

## 打法矩阵

| 形态 | 操作 | 判据 |
|---|---|---|
| alg=none / 变体 | header `{"alg":"none"}` 去签名(`none`/`None`/`NONE`/`nOnE`) | 服务端未硬编码期望算法 |
| HS256/RS256 混淆 | 用公钥当 HMAC 密钥签 HS256 | 服务端按 header.alg 选算法且用公钥验签 |
| 弱密钥爆破 | `hashcat -m 16500 jwt.txt wordlist` / jwt_tool | 库/示例默认密钥、短密钥、空密钥 |
| kid 注入 | `kid: ../../dev/null` / `kid: ' OR 1=1--` / kid 指向自己的 JWKS | kid 拼进文件路径/SQL/JWKS URL |
| jku/x5u 头注入 | 指向攻击者 JWKS 端点,放自己公钥 | 服务端信任 header 里的 JWKS 地址 |
| claim 语义伪造 | 改 `sub`/`uid`/`role`/`phone`/`isAdmin`/`type` | 只验签不查权限归属(水平/垂直越权) |
| **IDP 令牌签名缺验** | 第三方登录令牌(Google/Firebase/Apple/微信)只解 payload 不验签 | 见下 CVE-2026-13447 |
| 密钥泄露后续 | `secret_key_base`/JWKS 私钥/`.env` 泄露 → 无限自签 | 任意文件读取类洞的下一跳 |

## 实例: Mstore API(Firebase Phone Auth)未认证 JWT 伪造 — CVE-2026-13447(CVSS 9.8,2026-09)

WooCommerce/WordPress 移动端后端插件 **inspireui MStore API ≤ 4.20.0**:`FirebasePhoneAuthHelper::verify_id_token()` 只解码并检查 `alg`/`kid`/`aud`/`iss`,**从不调 openssl_verify() 校验签名** → 用 Firebase 项目的公开信息即可伪造任意手机号的身份令牌。
```
1) 自建 RSA 密钥对,自签一个 Firebase 风格 ID token(payload: 目标 phone_number / user_id / aud=该项目)
2) 调插件公开的手机登录端点(带该 token)
3) 插件信任 → 以该手机号身份登录/自动创建 WordPress 账号 → 接管已有账号(未认证远程,9.8)
```
**通用化(重点)**: 所有"用第三方身份令牌登录"的应用(Firebase/Auth0/Cognito/微信/Apple 登录)都要测这条 —— 抓包/读客户端确认服务端**是否真的回调 IDP 证书端点验签**,还是只 base64 解 payload。MStore 系还常见整片 REST 面(`/wp-json/mstore/v1/*`),拿到账号后接 WooCommerce 钱包/订单/卡密面。
- 来源: https://app.opencve.io/cve/CVE-2026-13447

## 验证标准
- 有效 = 用伪造令牌访问**需要身份的接口**返回目标用户真实数据(不是 200 空壳/HTTP 500)
- 改 claim 前先取一个合法令牌作基线,一次只改一个字段做差分
- 拿到 `secret_key_base` / JWKS 私钥才算闭环(可无限自签)

## 脚本
scripts/jwt_toolkit.py — 解码 / alg 变形 / HS-RS 混淆 / 弱密钥字典爆破 / kid 注入 payload 生成

## active_session 校验的 null 短路（2026-10 财神 C2 实锤）

Node/Express 自签 JWT 常见校验：
```js
if (user.active_session && decoded.sessionId !== user.active_session) return 401;
```
- `active_session = null` 的账号（新建/未登录）**跳过比对** → userId 对就给过，sessionId 随便填
- 从泄漏的 SQLite（如 `fisher.db`）读 `users.active_session`：非 null 用真实值签，null 账号随便签
- 判据：同一批账号 401/200 并存 = session 比对问题，不是签名问题
