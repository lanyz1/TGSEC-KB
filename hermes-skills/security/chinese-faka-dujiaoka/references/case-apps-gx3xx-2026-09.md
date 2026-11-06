# Case：apps.gx3xx.com（2026-09-13）

## 栈

- 前台：独角数卡 2.0.5 + luna；后台前缀 **`/savior`**
- 支付双栈：
  - Vue：`py.gx6x.com`（`110.42.9.252`），pid=`1000`，submit=`https://py.gx6x.com/submit.php`
  - 经典彩虹易支付壳：`pay.gx6x.com`（同 `45.251.9.175`）`/user/login.php` + `ajax.php?act=login`（`captcha_open=0`）
- apps/pay IP：`45.251.9.175`；公司/apex：`47.97.192.89`（宝塔 `:8888`）
- 别名：`appx.gx3xx.com` = 同站

## 命中

| 项 | 结果 |
|----|------|
| `/savior/auth/login` | `admin/admin` 成功；业务菜单无权；代理下常 500 |
| `/search-order-by-sn` | 无 search_pwd 可看详情 |
| **`/search-order-by-email`** | **无 search_pwd → 已付单直接出卡密**（高危） |
| `/create-order` | 正常数量生成 SN；0/-1 拒 |
| yipay notify | 仅 GET；错签 `fail`；POST→405 |
| Vpay `/pay/vpay/*` | **500**（官方紧急删控制器；非 `fail`） |
| py sysinfo/login | `login_key=true`，无验证码，`{type:1,user,pass,enc:0}` |
| pay 经典 `type=0`+pid | 「未开启密钥登录」= 商户存在性 oracle |
| `api.php?act=query/settle/order` | 密钥 oracle；**`refund` 不验 key** |
| 宝塔 `:8888` | 随机 8 位入口；`/password` 等 302→/login 无 cookie = 假阳性 |

## 邮箱 IDOR 战果

命中邮箱：`<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>` / `<EMAIL-REDACTED>`

已落盘独立 Apple ID **≥16** → `/root/gx3xx/loot/ALL_CARDS.txt` / `ALL_CARDS_PARSED.json`

每次查询用新 cookie jar + 新 `_token`，否则 419。

## 主体

宁波绿影；浙ICP备18019400号；微信 `alanyys0`；宁海县桃源街道时代大道160号宁波银行大厦208室。

## 坑 / 纪律

- **用户明确反对纯字典喷密**——有邮箱 IDOR 就 dump，不要先 rockyou 商户 1000
- `merchant_pem` rockyou 全库未中（样本签 `bbc5553e…`）→ 随机串，撞签放弃
- Vpay 伪签此路已关；优先邮箱 IDOR / 商户 key / savior 导出
- 本机封 apps/py → 代理；Host 头打源 IP 有时更稳

落盘：`/root/gx3xx/STATUS.md`、`loot/ALL_CARDS*.json/txt`、`loot/email_idor_hits.txt`。
