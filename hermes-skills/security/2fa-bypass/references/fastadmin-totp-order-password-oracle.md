# FastAdmin 代付 Google 2FA 校验顺序 → 密码 Oracle

> 荣盛代付 heimao 案例：TOTP 校验先于密码，泄露的 google_key 可绕过 2FA 防爆破

## 漏洞模式

正常预期：2FA 应该**增加**爆破难度。
实际行为：校验顺序 `TOTP → 密码` 导致拥有 google_key 的攻击者可以**完全绕过 2FA 的防爆破保护**。

## 攻击链

```
1. part/index 泄露 google_key（TOTP secret）
   ↓
2. 本地生成有效 6 位 TOTP code
   ↓
3. 登录请求: username + password_guess + valid_totp
   ↓
4a. 密码错 → 回显「密码错误」（TOTP 已通过，不消耗次数）
4b. 密码对 → 登录成功
   ↓
5. 等效于：TOTP 形同虚设，变成纯密码爆破
```

## 为什么有效

- `is_google=normal` 的账号：**先 TOTP 后密码**（先验 TOTP，通过后才验密码）
- 攻击者有 google_key → 永远能生成有效 TOTP
- 密码验证错误的回显不同于 TOTP 验证错误 → 密码 oracle
- 2FA 本应阻止的「密码爆破」变得毫无意义

## 与标准 2FA 绕过的区别

| 类型 | 本案 | 常规 2FA 绕过 |
|------|------|-------------|
| 前提 | 拥有 google_key | 无需密钥 |
| 手法 | 合法 TOTP + 爆破密码 | 空 code / 响应篡改 / 码复用 |
| 根因 | 校验顺序错误 | 实现缺陷 |
| 影响 | 2FA 沦为装饰 | 2FA 被绕过 |

## 防御

- 密码和 TOTP 应**同时**验证，不暴露哪个错了
- google_key 不应通过 `part/index` 泄露
- 登录失败应统一回显（不区分密码错/TOTP 错）
