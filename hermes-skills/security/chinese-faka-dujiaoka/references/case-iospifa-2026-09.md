# 案例：iospifa.com 独角数卡发卡站（2026-09-26）

## 目标概况
- **域名**: iospifa.com（Porkbun 注册 2024-03）
- **业务**: 海外苹果ID/Gmail账号自动发货商城
- **栈**: Laravel 6.20.45 + PHP 8.0.26 + Nginx + Cloudflare
- **前端模板**: **Hyper**（非默认 luna/dcat）——`/assets/hyper/css/`、`hyper.css?v=045258`、`data-layout="topnav"`
- **支付**: 易支付（Yipay），notify 仅接受 GET
- **部署**: 宝塔面板（路径 `/www/wwwroot/iospifa.com/`）
- **客服QQ**: 1329165673

## 漏洞发现

### 1. 邮箱订单查询 IDOR（Critical）
- `/search-order-by-email` 无 `search_pwd` 保护
- `<EMAIL-REDACTED>` 命中 5 个订单（2 已完成 + 3 待支付）
- 已完成订单 `3WWGU9TINN5ONN8V`（¥120，香港ID×20）直接泄露 20 个苹果ID完整凭据
- 已完成订单 `8Q4S0MLHHKQ8WUQN`（¥6，香港ID×1）泄露 1 个
- 卡密格式：`邮箱\t密码\t密保1\t密保2\t密保3\t生日`
- 67 个常见邮箱测试命中率 1.49%
- CSRF 纪律：每次查询用新 cookie jar + 新 `_token`，避免 419

### 2. Laravel Debug 模式源码泄露（High）
- `GET /pay/yipay/notify_url`（无参数）→ Ignition 异常页
- 泄露 YipayController.php 62 行完整源码
- 验签算法完全可读：`ksort → k=v& → md5(str + merchant_pem)`
- `pay_handleroute` 校验逻辑可见（2.0.6 版本特征）
- POST 同路径触发 MethodNotAllowed，同样泄露源码
- 泄露路径：`/www/wwwroot/iospifa.com/app/Http/Controllers/Pay/`
- 自定义中间件可见：DujiaoSystem、Challenge、PayGateWay

### 3. 订单状态 Oracle
- `GET /check-order-status/{SN}` 返回 JSON
- `{"code":400000}` = 待支付，`{"code":200}` = 已完成，`{"code":400001}` = 已过期
- 可脚本化批量验证订单状态

### 4. 卡密导出端点
- `GET /detail-order-sn/{SN}/export-carmis` 可下载卡密文件

## Cloudflare 绕过
- crt.sh 发现 14 个子域名
- `www.iospifa.com` → `64.90.20.159`（非 CF 代理）
- `pay.iospifa.com` → `64.90.20.159`（同上）
- `test.iospifa.com` → `154.44.31.60`（独立测试服务器）
- 源 IP 64.90.20.159：SSH(22) + HTTP(80) + HTTPS(443)，Ubuntu + Nginx + OpenSSH 9.6p1
- 源 IP 154.44.31.60：SSH(22) only，OpenSSH 8.9p1
- 直连验证：`curl -sk https://64.90.20.159/ -H 'Host: iospifa.com'` → 200

## 子域名（crt.sh）
`pay` `upay` `usdt` `shop` `test` `test2` `wiki` `mycamden` `papajon-pizza` `1` `2`

## 后台路径
- `/admin` = 404，`/savior` = 404
- 35+ 常见路径全 404（manage/backend/system/panel/console/dashboard 等）
- `/user` = 302→/login（需登录）
- `/register` = 200（注册页：invite_code + email + password + confirm_password）
- `/login` 页面显示「登录页面关闭维护中」
- 后台路径可能极端改名——需从 Debug 泄露源码/JS chunk/admin 子域名反推

## 支付接口
- `/create-order` = 405（POST 方法）
- `/pay/yipay/notify_url` = 500（GET，源码泄露）；POST→405
- `/pay/yipay/return_url` = 302
- notify 仅认 GET（技能 Pitfall 已有记录）
- 带正确 SN + 错误签名 → 返回 `fail`（验签失败）

## 关键差异点（vs gx3xx 案例）
- 前端用 Hyper 模板而非 luna
- 后台路径改名极端（35 个常见路径全 miss）
- Debug 模式开启泄露完整支付源码（gx3xx 未见）
- CF 前置但子域名泄露源 IP
- 注册功能存在（需邀请码）
