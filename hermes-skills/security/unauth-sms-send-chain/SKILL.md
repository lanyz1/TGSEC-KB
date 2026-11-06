---
name: unauth-sms-send-chain
description: >-
  Use when 平台有免鉴权的短信发送/校验码接口（passport/sendSms、validatecode、resetpwd）：
  可无限发短信刷成本，并能拼成「发码→校验码可爆破/回显→重置密码」的账号接管三步链。
---

# 未鉴权短信 + 重置密码三步链

## 指纹
- `POST /passport/sendSms`、`/api/sms/send`、`/api/captcha/sms`、`/sendCode`、`/msg/send`
- 请求体只有手机号与一个前端生成的 `sign`/`timestamp`（可离线复算）
- 返回 `{"code":0,"msg":"发送成功"}` 且**无图形验证码、无频率限制、无登录态**

## 判法
1. 空 cookie 发一次 → 200 且真收到短信（用自己号）
2. 同一号连发 5 次 → 全部 200 = 无限速；换 10 个号 → 不封 IP = 可批量
3. 发送接口的 `sign` 若是 `md5(phone+固定密钥)`，从 JS 取密钥即可离线批量

## 接管三步链
1. **发码**：`sendSms(phone, type=reset)` → 目标手机收到验证码
2. **校验码接口**：`POST /passport/validatecode {phone, code}` —— 常见缺陷：返回布尔差异、无尝试次数限制、`code` 可枚举（4 位数字 10k 次/分钟）、错误码区分「码错」与「码过期」
3. **重置**：`POST /passport/resetpwd {phone, code, newpass}` —— 把上一步拿到的 `ticket`/`token` 直接带上
- 若 `/validatecode` 返回 `{"code":0,"ticket":"..."}` 且 ticket 不绑会话 → 直接换任意账号

## 放大
- 短信轰炸：目标号连发 → 成本消耗 + 骚扰（单号 50 条/分钟）
- 号码枚举：发送接口对「已注册/未注册」返回不同 code → 全量用户枚举 oracle
- 与之配套的 `alogin`/`data.` 子域常无 WAF，从旁站打主站

## 判据与证据
- 记录：接口、请求体、响应码、收到短信的截图时间戳、连发次数
- 只对自有号码实测；不对真实用户批量发送
