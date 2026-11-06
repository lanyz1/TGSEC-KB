<!-- archived from /root/.hermes/skills/security/2fa-otp-bypass/SKILL.md on 2026-10-21 -->

---
name: 2fa-otp-bypass
description: "2FA/MFA/OTP绕过时使用。触发: 2FA绕过, OTP爆破, MFA bypass, TOTP, 双因素认证。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, 2fa, otp, mfa, totp, bypass, account-takeover, surveyengine-absorbed]
    related_skills: [jwt-attacks, captcha-registration-bypass, frontend-auth-bypass, surveyengine-knowledge-pack]
---

> 归档卡：原目录 `/root/.hermes/skills/security/2fa-otp-bypass`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/2fa-otp-bypass/…')`，不要相对 `references/legacy/` 解析。

# 2FA/MFA 绕过完整手法

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\2fa-bypass\SKILL.md`,296 行全量)。

## 分流决策树
```
遇到 2FA
 ├─ OTP 位数少(4-6)+ 无速率限制 → §1 暴力破解
 ├─ 错误/正确前缀响应分流 → §1.5 前缀预言机(先于全量爆破)
 ├─ 返回 {"success":false} 类型响应 → §2 响应篡改
 ├─ 2FA 独立步骤(/verify 端点)→ §3 步骤跳过
 ├─ 有备份/恢复码 → §4 备份码
 ├─ 密码重置不需 2FA → §5 重置绕过
 ├─ OAuth/SSO 登录不经过 2FA → §6 OAuth 绕过
 ├─ TOTP 密钥 API/Cookie 泄露 → §7 密钥提取
 └─ 基于 SMS → §8 SMS 路径
```

## §1 OTP 暴力破解
1. 先探测速率限制: 4-5 个错误 code 看是否 429/锁定
2. 无限制 → 全量 000000-999999(Python requests 循环或 Burp Turbo Intruder parallel=100)
3. **速率限制绕过**: 换 IP/代理池;换 Session 重新登录;null byte `{"otp":"12345\u0000"}`;数组注入 `{"otp":["123456"]}`;整数类型 `{"otp":123456}`(绕字符串比较)

## §1.5 OTP 前缀预言机(先于全量爆破!)
验证器按前缀分段比较时,把 10^6 压成 ~10×位数 次。
- ⚠️ 全程锁死**同一个 pre-MFA session**,中途重新登录会换 OTP 前缀进度作废
- 先扫 1 位 otp=0..9,观察 status/长度/文案是否 DIFF → 有 DIFF 记下该位,拼下一位继续
- 无 DIFF → 回 §1 看速率限制,或走 §3 步骤跳过

## §2 响应篡改(最简单)
- 拦截响应 `{"success":false}` → 改 `{"success":true}`(Burp intercept / mitmproxy `--modify-body '/api/verify-otp:false:true'`)
- **验证是否真依赖响应**: 1) 正确 OTP 成功响应改 false 还能继续? 2) 错误 OTP 改 true 直接跳转?
- **服务端 Session 绕过(关键)**: 有些只做客户端 redirect 未设 server-side session → 直接访问 2FA 后页面

## §3 步骤跳过
- 输完密码但未完成 2FA 的 session → 直接访问 /dashboard、/api/user/me
- Laravel: middleware 查 auth 不查 2fa_verified;Express: JWT 含 2fa_completed=false 但后端不验证
- JWT 解码改字段 → 走 jwt-attacks 技能重签

## §4 备份码
- 若 API 泄露备份码: `GET /api/user/backup-codes`
- 格式可预测(8位数字/xxxx-xxxx)→ 枚举
- JS 硬编码: `grep -oE '"backup[^"]*":[^,}]*' app.js`

## §5 密码重置绕过 2FA
- 重置密码后 magic link 直接登录不要求 2FA(常见)
- ATO 后禁用 2FA: `DELETE /api/2fa`(带新 token)
- ⚠️ 只动自己注册的号,默认不提交邮箱发信(用户红线)

## §6 OAuth/SSO 绕过
- 目标支持 Google/GitHub OAuth → OAuth 登录常不经过 2FA
- SAML SP-initiated SSO,IdP 侧常不强制 2FA

## §7 TOTP 密钥提取
- 设置时 QR URL 泄露 secret: <REDACTED>
- API 直接返回 secret: `GET /api/2fa/setup` → 提取后 pyotp 生成任意 OTP:
```python
import pyotp, time
totp = pyotp.TOTP('JBSWY3DPEHPK3PXP')  # Base32
print(totp.now())
```

## §8 SMS OTP
- 服务端把 OTP 返回前端 JSON(极不安全)→ 直接读 code 字段
- JS 泄露 Twilio 等 SMS API key: `grep -oE 'AC[0-9a-f]{32}|SK[0-9a-f]{32}' app.js`

## §9 Cookie/Header 混淆
- Cookie `2fa_verified=0` → `1`;`mfa_complete=true`
- Header `X-2FA-Verified: true`、`X-MFA-Skip: 1`

## 成功口径
| 档 | 条件 |
|---|---|
| L1 | 发现 2FA 弱点(无速率限制/响应可篡改/步骤可跳过) |
| L2 | 绕过 2FA 进入账户 |
| L3 | 接管完成(改密/改绑定邮箱) |

## Pitfalls
- 用户禁止对他人账号高速尝试;只测自己注册号;SMS 劫持影响真实用户须授权内谨慎
- 前缀预言机必须锁死同一 session
- OTP 全量爆破前一定先测速率限制,别一上来 100 万跑(会封 IP 且用户红线)

## 2026-10 数组型参数打崩校验（PHP/Symfony）
- `_code[]=1` / `code[]=x` 让 PHP 收到 array；`hash_equals($secret, $code)` 抛 `TypeError`
- debug 异常页会序列化调用栈帧参数，`$secret` 直接可见（Sonata GoogleAuthenticator 实测）
- 拿到 secret：`oathtool --totp -b <SECRET>` 生成合法码
- prod 无堆栈时改测「根本不校验」：code 缺失 / 空 / `000000` / 上次用过的码
- 同族：`totp_enabled=1` 但服务端没写 `if (!$totp) reject`，直接放行（自研客服工作台实测）
- 判据优先级：TypeError 泄露 > 空码通过 > 重放旧码 > 爆破
- 注意：只有 debug/异常页开启才会泄露参数；否则仅是 500，别写成通杀
