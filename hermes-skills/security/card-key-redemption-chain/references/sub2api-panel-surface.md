# Sub2API 面板面（卡密生态最普遍的面板，同源代码站成群）

## 公开路由（免登录）
`/redeem` `/subscriptions` `/usage` `/announcements` `/channels/available` `/groups/rates` `/channel-monitors`
- `/redeem` 虽公开，实际 302 → `/login?redirect=/redeem` ⇒ 兑换需登录。

## API
- 基址 `/api/v1`（前端 bundle 里由 `api/v1` 常量拼出，正则挖 `api/v1` + 具体路径）。
- 注册：`POST /api/v1/auth/register`。
- 管理端：`/api/v1/admin/redeem-codes`（list / get / generate / delete）。
- 兑换码类型：`balance` / `concurrency` / `subscription` / `invitation`。
- 原生兑换码生成：`crypto/rand` 16 字节 → hex → 四组 `XXXX-XXXX-XXXX-XXXX`（32 位 hex）。

## 注册邮箱后缀白名单（服务端强校验）
- 只放 `@qq.com` / `@gmail.com` / `@163.com`；错误体 `{"reason":"EMAIL_SUFFIX_NOT_ALLOWED","metadata":{"allowed_suffixes":...}}`。
- 伪域一律 400：`notqq.com`、`x163.com`、`qq.com.evil.com` 全拒 ⇒ 判定是**后缀全匹配**，不是 contains。
- 临时邮箱服务的域名不可能在白名单内 ⇒ 撞到这层就是**硬卡点**：如实交底「需真实 QQ/Gmail/163 邮箱注册」，停止换邮箱试错。

## 渗透注意
- 管理端兑换码接口是**发卡能力**所在：拿到管理票据即可自造兑换码/看已发码；比破解兑换流程更值。
- 该面板的登录限速键常为伪造客户端 IP 头（XFF 系）——与其等冷却不如逐发轮换头。
- 面板的 `/v1` 常作为 API 基址对外服务（OpenAI 兼容），其 key 就是用户「导入后拿到的凭据」。
