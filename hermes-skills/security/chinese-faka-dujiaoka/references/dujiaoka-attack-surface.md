# 独角数卡 / dujiaoka 攻击面（Laravel + Dcat）

开源：`assimon/dujiaoka`。生产常改后台前缀、阉角色、接易支付。

## 指纹

- Cookie：`XSRF-TOKEN` + 站点 session（如 `id5_session`）
- 静态：`/vendor/dcat-admin/`、`/assets/luna/`（luna 模板）
- 标题/页脚：「独角数卡」、Powered by Dcat Admin
- robots 典型：
  ```
  Disallow: /savior/   # 或 /admin/
  Disallow: /pay/
  Disallow: /bill/
  Disallow: /pay-gateway/
  Disallow: /order-search/
  Disallow: /detail-order-sn/
  ```

## 默认与改名

| 项 | 默认 | 备注 |
|----|------|------|
| 后台前缀 | `/admin` | 常改成 `/savior` 等 |
| 管理员 | `admin` / `admin` | **必须验证菜单权限** |
| 安装 | `/install` | 上线后应关 |

登录成功若全站「无权访问」：口令对、角色空/只读——继续找另一管理员、未授权 API、或支付旁路，不要假装已控库。

## 前台高价值路由（common/web.php）

```
GET  /buy/{id}
POST /create-order          # gid, by_amount, email, payway, _token；可选 coupon_code / search_pwd
GET  /bill/{orderSN}
GET  /detail-order-sn/{orderSN}
GET  /order-search
GET  /check-order-status/{orderSN}   # JSON: 400000 wait / 200 success / 400001 expired
POST /search-order-by-sn             # order_sn
POST /search-order-by-email          # email + 可选 search_pwd
POST /search-order-by-browser        # cookie dujiaoka_orders
```

### 订单 IDOR

- 许多站 **关闭查询密码** 时，`search-order-by-sn` 仅凭 SN 出详情（商品/邮箱/金额/状态）
- **`search-order-by-email` 同款高危**：无 `search_pwd` 时，短数字/常见邮箱可直接拉出 **已付订单卡密**（页面 `data-clipboard-text`）。优先测 `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` 等，再扩短 QQ 号段
- CSRF：每发一封邮箱查询用 **新 cookie jar + 新 `_token`**，复用易 419 Page Expired
- 无效 SN：可能 200 + 「出现错误了哟~」同类模板——用标题/正文区分，别只看 status
- SN 多为随机大写串（如 16 位），盲枚难；优先从邮箱 IDOR、下单 cookie、泄露日志拿 SN
- **用户纪律**：有邮箱/SN IDOR 就 dump，不要先开 rockyou 喷商户密码

### 下单

- `by_amount=0/-1` 常业务拒绝；正常数量进 `/bill/{SN}` 仍是待支付
- 支付方式 `payway` 为通道 ID；错误 ID 也可能生成单但后续 500

## 易支付（YipayController）

组装参数：`pid,type,out_trade_no,return_url,notify_url,name,money` → `ksort` → `md5(k=v&… + merchant_pem)`。

- `notify_url` 常为 `url(pay_handleroute . '/notify_url')`，例 `/pay/yipay/notify_url`
- **方法**：有的部署 **只认 GET**（POST→405 Method Not Allowed）——先 OPTIONS/GET/POST 探清
- 验签失败返回纯文本 `fail`；缺字段可能 500
- `merchant_pem` 常是随机密钥（文档示例即 32 位）：rockyou 撞签可放弃；优先：
  1. 后台支付配置页（需权限）
  2. 易支付商户后台（`py.*` / submit 同域）
  3. 配置文件/备份泄露
- `api.php?act=refund` 可能 **不验 key**（空/错 key 都回「未开启商户后台自助退款」）——别当密钥 oracle；`query/settle/order` 仍是「商户密钥错误」oracle
- 有 key 后：按同算法签 `trade_status=TRADE_SUCCESS` 等字段 → GET notify → `check-order-status` 应变 success → 详情页出卡密
- **Vpay（2.0.5）**：官方紧急通知删 `app/Http/Controllers/Pay/VpayController.php`。站上 `/pay/vpay/*` 若统一 **500**（不是纯文本 `fail`）= 控制器已删，停止伪签。2.0.6 才普遍加各支付 `pay_handleroute` 校验

## 易支付商户面板（现代 Vue）

例：`https://py.example.com/user/`（Vite + Element Plus）。

- `GET …/user/auth/sysinfo`：`login_key` / `captcha_open_login` / `login_code` / `public_key`
- `POST …/user/auth/login` JSON，常见体：
  - 密码登录：`{type:1,user,pass,enc:"0"|"1",remember}`（`enc=1` 时 pass 为 JSEncrypt/PKCS1 后的 base64）
  - 验证码登录：`type:2` —— 若未开启会回「未开启验证码登录」
- `api.php?act=query&pid=&key=` 可当 **密钥对错 oracle**（「商户密钥错误」vs 其它）
- 登录喷密前确认 sysinfo 开关；有极验时再接 captcha 流
- 生产常 **双栈**：Vue `py.*` + 经典彩虹壳 `pay.*`（`/user/login.php`、`ajax.php?act=login`、CSRF+PHPSESSID）。经典密码口占位是 **邮箱/手机**；`type=0`+`user=pid` 走密钥登录（未开启会回「该商户未开启密钥登录」——可当商户存在性 oracle）

## 宝塔面板（同机 apex）

- `:8888` 开随机 8 位安全入口时：错路径统一「安全入口校验失败」
- `/password` `/site` `/system` `/api` 等会 **302→/login 且无 Set-Cookie** = **假阳性**，不是入口
- 真入口：直接 200 登录表单，或带 session/bt cookie 的跳转

## Dcat 后台注意

- AJAX 登录常返回 JSON：`status:true` + `then.action=location`
- 列表页可能壳 HTML +「无权访问」；导出 `?_export_=` 同样吃权限
- 改自己密码在 `auth/setting`，**不提权**

## 风控

短时大量下单/登录后源站可能对攻击 IP 超时；公司站/apex 仍可能通。换代理后再打 apps/py，勿把封禁写成「站挂」。CF 1006 / 本机 403 先换 Tor 再判站挂。

## Hyper + epusdt（柜台查单常漏签）

见 `references/epusdt-unauth-check-status.md`。`pay-gateway` 跳柜台 → HTML `order-trade-id` → `GET /pay/check-status/{trade_id}` 无鉴权是预言机不是伪回调。nginx 403 时用 `/index.php/pay/epusdt/notify_url`。
