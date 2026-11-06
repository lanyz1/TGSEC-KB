---
name: usdt-faka-filter-saas
description: "Use when USDT faka, epusdt, order store, or filter SaaS."
version: 1.0.0
tags: [faka, dujiaoka, xiaoqi, epusdt, usdt, filter-saas, exeprog, appfilter, fixed-address, marketing-shell]
---

# USDT 发卡 / 筛选 SaaS / 营销云控壳

授权红队里 **固定 USDT 收款** 的数字货商城、独角/小柒发卡、社媒筛号后台，以及 WP「云控」软文壳。
**不是** approve 盗 U（对照见下）。

Overlap note: 与 user-owned `crypto-web-campaign-patterns` 同域；若已 `hermes curator adopt` 该技能，优先合并进它，本技能可作并行入口。

## When to load

- 用户问「是授权盗U吗」且站像发卡/号商/能量/筛号/云控介绍页
- `dujiaoka_locale` / unicorn / 小柒.APP / robots `manage-<hex>` / epusdt `:8000`
- `order.*` + `/assets/store.js` + `/api/v2.php?action=`
- `data.*/login.php` / appfilter / 智域筛选 / Nexora
- WP 路径 `/whatsapp/cloud-control/` `/telegram/cloud-control/` 但无真实面板

## 先分类（CRITICAL）

用户先问定性 → **先 1 屏对照表再打**。

| 形态 | 信号 | 否决盗U | 下一刀 |
|------|------|---------|--------|
| 授权盗U | approve、`/payment-config`、spender | 否（就是） | defi/caishen |
| 独角/小柒发卡 | buy/create-order/bill、yipay/epusdt | 是 | `references/dujiaoka-xiaoqi-epusdt.md` |
| 定制 JSON 商城 | store.js → api/v2.php | 是 | `references/custom-order-v2-store.md` |
| 筛号 SaaS | login/register、金币、upload_task | 是 | `references/filter-saas-appfilter.md` |
| WP 云控软文 | 介绍页+外链 order/appfilter | 是 | 跟外链，勿当 C2 |
| 能量 MiniApp | freeEnergyBot、initData | 是 | crypto-web tron-energy ref（若可用） |

## 营销云控页铁律

`/whatsapp/cloud-control/` 标题再像面板，**栈是 WP 就先抠外链**（order / data / appfilter / t.me）。
3 次确认无运行时 API 后：报告「销售壳」+ 转向关联站，禁止空耗 path 字典装 C2。

## 独角 / 小柒 + epusdt（摘要）

1. robots 找 `manage-<16hex>`；小柒可无验证码
2. 未授权下单 → bill → 收银台 `data-clipboard-text` 收款地址
3. 查单：有的 **只要 SN**（pttget）= 隐私面
4. 老独角≤2.0.4 伪造脚本 **不能** 直接套 V14；先抓 pid/key
5. epusdt：`hello epusdt` 在 pay 子域/`:8000`；API 无 `api_token` 全 401

## 定制 order v2 商城（摘要）

1. RE `store.js` 的 `api(action,data)`
2. **`action=check` + 仅 order_id`** → 整单（buyer_tg、**bcrypt 查询密码**、GDrive、机器码教程）= CRITICAL
3. create_order 抠统一 `pay_address`；claim_txid ok ≠ PAID
4. 金额 body 篡改常被服务端重算

## 筛号 SaaS（摘要）

1. 开放注册 + **test/demo 弱口令**（曾测 test/test123；**会改密/锁定，勿当永活**）
2. `/admin/login.php` 常无验证码；**data 后台可能多 `step=credentials`（2FA 预留）**
3. 登录后 download_result/uploaded；测 IDOR（看 attachment+哈希，勿只看 200 HTML）
4. 充值页地址常与商城 **同一 TRC20**
5. **用户喊停爆破 / 字典空转时**：立刻切逻辑面（见 ref）——fixation、订单 IDOR 读、proof、CSRF、审核 XSS 饵；禁止死磕 admin/MySQL/SSH 字典

## 铁律

- 「是授权盗U吗」→ 先表后打
- 切换目标：旧 `/tmp/<t>/REPORT.md` 再开新目录
- 无 spender 钥禁止假装 transferFrom
- claim/notify 端点存在 ≠ 免支付发货
- **跨用户写入 IDOR 必须双账号验证**（A 建单 B 写）；同账号历史单当「写入成功」= 误报
- **TXID/备注「有 onerror」≠ XSS**：先看是否在 `<code>`/实体编码里；用户端编码仍可挂审核端饵

## References

- `references/dujiaoka-xiaoqi-epusdt.md`
- `references/custom-order-v2-store.md`
- `references/filter-saas-appfilter.md`
- `references/approve-vs-fixed-usdt-table.md`
