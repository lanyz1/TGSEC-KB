---
name: password-reset-methodology
description: 密码重置与用户注册/越权修改方法论。当目标存在忘记密码/密码重置、验证码回显、校验绕过、任意用户密码修改、越权注册（registersysuser、goedituser 等接口）、thinkphp…
metadata:
  tags: "密码重置,密码修改,验证码回显,验证码,短信验证码,校验绕过,任意用户密码修改,任意用户,越权,注册,registersysuser,goedituser,login_tologin.do,thinkphp,商城,登录,重置,password,reset,assessment,授权"
  category: "exploit"
---

# 密码重置 / 越权注册与修改方法论

## 适用场景

涉及密码找回、验证码、用户注册/资料修改接口时使用。

## Phase 1: 密码重置链路分析

```
忘记密码流程
├── 步骤：手机号/邮箱 → 验证码 → 重置密码
├── 每个步骤的请求/响应都要抓包分析
└── 重点：验证码如何校验、如何返回、是否可重放
```

## Phase 2: 验证码问题排查

1. **验证码回显**：响应包/接口返回中直接包含验证码（短信/图片/邮箱验证码回显）
2. **验证码可爆破**：验证码位数过短（4 位）且无频率限制
3. **验证码校验绕过**：删除/置空 code 参数、修改响应、并发重放、万能验证码
4. **短信轰炸/发送接口未限频**：发送验证码接口无次数限制

## Phase 3: 任意用户密码修改与越权注册

- 重置接口替换目标手机号/用户 ID：`mobile=<目标>&code=<自己的验证码>`
- 注册/改资料接口越权：`registersysuser`、`goedituser` 等接口无鉴权或未校验数据归属
- 校验方式：用 A 的验证码重置 B 的账号；低权限/未登录调用管理类注册接口
- 示例：`login_tologin.do` 类登录/注册入口存在鉴权绕过时，可未授权注册管理员

## Phase 4: thinkphp 商城短信验证码

- 商城类系统（thinkphp 框架）短信验证码常见问题：验证码存 Session 可并发、接口可重放、返回包泄露 code
- 登录/注册/找回密码三处验证码逻辑分别测试

## 授权边界

- 仅限授权渗透测试
- 不批量重置他人账号；验证到可越权即停

## 关联

- 鉴权绕过补充 → 401-403-bypass
- 图片验证码识别绕过 → captcha-bypass-methodology

## OTP 收件邮箱可指定 → 忘记密码直达改密（2026-09 xmnyme 实战）
- `POST /api/notify/send_email {to:<攻击者邮箱>, type:2, area_id:2}` —— 收件地址由请求体决定，验证码发到攻击者邮箱
- `POST /api/user/forget_password {account, new_password, auth_code, secondary_password, type:email}` —— 不校验请求者身份，只校验 auth_code
- 合起来：任意邮箱账号 → 改密 → 直接登录
- 附带观察：连发触发 `Too Many Attempts`（限速在登录不在发码）；换邮箱前缀继续；部分账号 `LOCKED` 后再试仍成功 → 锁定态未持久化
- 判据：收件箱收到目标账号的验证码 + 新密码能登录
