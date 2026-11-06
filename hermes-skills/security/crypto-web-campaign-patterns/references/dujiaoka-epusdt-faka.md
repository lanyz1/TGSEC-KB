# 独角数卡 / 小柒发卡 + epusdt / 易支付

类级：Laravel 发卡（Dujiaoka 系及定制「小柒.APP」），数字货自动发货 + 第三方/链上收款。
**不是**授权盗 U。

## 指纹

| 信号 | 含义 |
|------|------|
| cookie `dujiaoka_locale` / `_session` + `XSRF-TOKEN` | Laravel 发卡 |
| `/assets/unicorn/` CSS | 独角 unicorn 主题 |
| robots `Disallow: /manage-<hex>` | **后台路径泄露**（laotie 实测） |
| 标题「小柒.APP管理后台」V14.x | 定制后台，非原版 admin |
| `hello epusdt, https://github.com/assimon/epusdt` | pay 子域或 `:8000` 支付中台 |
| `/buy/{id}` · `POST /create-order` · `/bill/{SN}` | 标准购物流 |
| `/pay/yipay/notify_url` 存在（fail/500） | 易支付回调面 |
| `/pay/epusdt/notify_url` | epusdt → 商店回调 |

## 攻击顺序

1. **分类**：确认无 approve / 无 payment-config spender
2. **未授权下单**：`GET /buy/{gid}` 抽 `_token`+字段 → `POST /create-order`（gid/email/by_amount/payway[/spec_id/checkout_token/search_pwd]）
3. **账单/支付**：`/bill/{SN}` 选 payway → `POST /bill/{SN}/pay` 或 `pay-gateway/...` 跳 epusdt 收银台
4. **收银台 RE**：HTML `data-clipboard-text` = **金额 + TRC20 地址**；跟链上归集
5. **查单**：`/order-search` — 有的站 **只要 order_sn**（无查询密码）→ 隐私/枚举；有的要 email+pwd 且 429
6. **后台**：robots/字典 `manage-<md5前16>`；小柒可无验证码但有失败限流；弱口勿只打 admin/admin123
7. **回调伪造**：
   - **老独角 ≤2.0.4** 才可能 merchant_id=密钥类脚本（见 security-suite `dujiaoka-notify-forgery.yaml`）
   - **V14/小柒/加固站**：必须先从支付跳转抓 **真实 pid + key**；盲签 yipay 多恒 `fail`
   - epusdt create/notify：`signature = md5(sort(k=v)& + api_token)`（assimon 文档）；弱 token 字典常 401「签名认证错误」
8. **卡密预选**：`/goods/{id}/selectable-carmis` 需规格；可能预占/枚举面
9. **源站**：CF 后若 A 直连（如 Vultr）→ nmap；`:8000` epusdt 与 443 同机常见

## 实测锚点（2026-09）

| 站 | 形态 | 要点 |
|----|------|------|
| laotie.app | 小柒 V14 + CF | robots 泄 manage-73615…；订单 `LAO…`；payway 1/2/5；yipay 在；老伪造未中 |
| pttget.com | 独角 unicorn + 源站 66.42.44.209 | payway=23 USDT-TRC20；SN `20260910…`；查单 **无密码**；epusdt 收款 `TQCMsTm8QKGnoyHZRGQ6QVSMiyA6eZggk4`；归集 `TA3tfg1Z…` |
| inspifa.com | ThinkPHP 号商 jingdian | 另栈；支付宝+USDT；非独角 |

## 坑

- 路径 `/admin` 404 ≠ 无后台（定制 manage-hash）
- `install` 回到首页 1MB = SPA/软路由，不是可装
- create-order 200 账单 HTML 不是 JSON — 从 `Location`/canonical/`/bill/SN` 抽单号
- 查单 429：换面（支付/后台/链上），别死刷
- epusdt 根路径 200 文本 hello ≠ 未授权下单接口；`/api/v1/order/*` 无签全 401
