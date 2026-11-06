# 聚合支付 fork（Epay / 彩虹易支付系）闸门速查

国产二开聚合支付网关是本用户目标池的常见品类。以下为已实测的落点，用于快速跑完「五道闸门」。

## 表族
- `.env DB_PREFIX=pay` ⇒ `pay_*` 是**真身**；`pre_*` 往往原样保留并**镜像同一份数据**（行数一一对应）。计数与影响量化要写明两族各多少行。
- 关键表: `*_user`(商户) / `*_order`(订单) / `*_settle`(结算) / `*_config`(站点配置) / `*_channel`(通道) / `*_plugin`(插件目录) / `*_transfer`(代付) / `*_cache`(config、tongji、`order_YYYYMMDD` 缓存块)。

## `*_config` 关键键（决定闸门）
| 键 | 语义 |
|---|---|
| `syskey` | 全局无主签名密钥（常被弱签分支直接使用，SQLi 可拖） |
| `keytype` | 1 = 商户请求走 RSA |
| `reg_open`/`reg_pay`/`reg_pay_price`/`reg_pay_uid` | 开放注册 / 注册需付费开通支付 / 金额 / 收款商户 ⇒ 商户号获取成本 |
| `settle_open` | **1 = 关闭商户端自助提现**（`user/ajax2.php` 里 `withdraw` 仅 `settle_open∈{2,3}` 开） |
| `settle_money`/`settle_rate`/`settle_fee_min|max` | 自动结算门槛与费率 |
| `user_refund` | 商户端退款开关 |
| `test_open` / `test_pay_uid` | 测试支付开关与主体商户（常 = 站长主账号） |
| `cronkey` | 定时任务弱密钥（只报告，绝不调用：脚本跑结算类资金作业） |

## `*_user` 关键列（权限面）
`money`(余额) · `settle` / `refund` / `transfer`(代付权限) / `pay`(支付开关) · `keylogin` · `pwd` · `settle_id`/`account`(结算账号) · `voice_devid` / `voice_order`(收款设备号)。

## 闸门落点（实测）
1. **未授权弱签读单/退款**: `api.php` 分支里只有 `act=order`(读单) 与 `act=refundapi`(退款) 只用 `syskey` 派生的签名、**不带 pid**；`query`/`settle`/`orders`/`refund` 都需 pid + 商户密钥。用**错误 key** 探存在性即得「密钥错误」类回显，**不带正确 key**。
2. **上限校验**: `lib/Order::refund()` 同时有「单次 ≤ realmoney」与「≤ 剩余可退(realmoney-refundmoney)」两道校验，且必须有 `api_trade_no`（真实支付过）⇒ 无超额、无凭空造钱。读这类分支必须**整行**读，截断打印会造出假的「空 if」。
3. **动作能力**: `Plugin::isrefund($name)` = `plugins/<name>/<name>_plugin.php` 里 `method_exists(<name>_plugin,'refund')`。退款链能否真正打到通道，取决于该表 `channel.plugin` 对应插件是否实现 `refund`。
4. **扣款侧**: `Order::refund` 会 `changeUserMoney($order['uid'], -$reducemoney, '订单退款')` ⇒ **退款 = 商户余额损失**（破坏型，钱回原买家）。
5. **收款码下单链（可得钱型）**: `gateway.php` 常带 `$nosession=true`，唯一身份 = 设备号 `sn` = 商户列的 `voice_devid`；链路 = 取商户 → `INSERT order` → `Channel::submit` → `Plugin::loadForSubmit` 真扣付款码。**零写入证明**用空 `data` 或**不存在的 `sn`**（都在 `INSERT` 之前返回）。
   ⚠️ `voice_devid` 通常是**商户后台可自填字段**（形如 `user/ajax2.php` 的 `case 'edit_voice'`，零校验）⇒ 「需要真实设备」是误判，链其实自主可控。
6. **出款闸门（决定能否变现）**: `user/transfer_add.php` 类代付端点 = 登录密码 + `$userrow['transfer']` 权限列 + 提交后 **等待管理员审核**；加上 `settle_open=1` 关闭商户自助提现 ⇒ 盗刷/归集进来的钱取不出去，必须再拿 admin 或社工。

## 建议探测顺序
资金坐标（读 `*_settle` + `*_user.money` + 订单 count/sum）→ `api.php` 分支鉴权表 → 通道插件 `refund`/扫码能力 → `gateway.php` 身份闸门（谁能设 `voice_devid`）→ 出款闸门 → 成表交付。
