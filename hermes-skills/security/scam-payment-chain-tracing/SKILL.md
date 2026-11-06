---
name: scam-payment-chain-tracing
description: "Use when tracing a scam platform's victim money flow."
---

# 诈骗/资金盘 法币资金链溯源

目标不是拿权限,而是回答"受害人的钱最后进了谁的口袋"。拿一个低权账号就能走完全程:充值下单 → 聚合商收银台 → 二维码解码 → 境外马甲商户。

## 何时使用

- 已能登录某资金盘/杀猪盘/博彩 App,要出"资金归集点"结论
- 报告需要把"诈骗实施端"和"境外收款层"连起来
- 平台有自己的充值页(不是纯链上 USDT)

## 第 0 步: 处理短 TTL token

这类平台的用户 token 往往 3-5 个请求就失效(返回 `登录已失效,请重新登录`)。

**每个请求前重新登录**是唯一可靠做法,批量脚本里写成 `login()` 每调用一次。别用会话复用,否则整批 401 会被误判成"接口不存在"。

## 第 1 步: 从打包产物抽支付接口

uni-app / Vite 打包后每个业务模块一个 `xxx.<hash>.js`,内容是薄封装,接口字符串是明文:

```js
function a(){return e("/app/recharge-channels",{needAuth:!0})}
function r(e){return t("/app/recharge",e,{needAuth:!0})}
```

正则扫全量模块文件(`["'`](/app/[A-Za-z0-9/_-]+)["'`]`),比猜路径快一个数量级。常见面:

- `/app/recharge-channels` `/app/withdraw-channels` `/app/banks`
- `/app/deposit-withdraw-config` `/app/user-withdraw-accounts`
- `POST /app/recharge` `GET /app/withdraw-orders?page=&pageSize=&walletKey=`

## 第 2 步: 下单探通道(不付款)

`POST /app/recharge {amount, rechargeChannelId, scene}`

- **金额阶梯**: 小额(10)常被风控挡 —— `该金额10.00没有可用通道,请联系客服检查风控`;100/500/1000 通常放行
- **错误即情报**: `无法取得可用的支付通道[productId=8888,mchId=20000034]` 直接泄聚合商商户号
- 成功返回 `data.url` = 收银台;不同 channelId 对应不同聚合商(微信 JSAPI / 支付宝收银台 / 四合一 / 代付)

## 第 3 步: 收银台取 QR

`curl <cashier_url>` → HTML 里 `qr_value:"<EMVCo TLV>"`;有的通道把参数 base64 塞在 URL 的 `data=` 里。

## 第 4 步: 解码与判读

用 `scripts/emvco_qr_decode.py <字符串>`。关键 tag:

- `00` 版本 / `01` 11=静态 12=动态
- `26` 商户账户信息: `A000000615`=UnionPay, `RHBQR`=RHB Bank Malaysia, `DuitNow`(MY), `QRIS`(ID)
- `53` 货币(458=MYR, 156=CNY, 840=USD)
- `54` 金额 / `58` 国家 / `59` 商户名 / `60` 城市 / `61` 邮编 / `62` 参考号 / `63` CRC

结论一句话写清三段:**本币金额 → 外币金额、收单机构、商户名+城市**。

实战样例(2026-10 某"人民资产"盘): ¥100 订单 → UnionPay QR → RHB Bank Malaysia → 商户 `COOLING POINT NILAI`,56000 吉隆坡,MYR 60.76。即人民币在马来西亚落地成马币,实体店当马甲。

## 第 5 步: 顺手拿漏斗定价与话术

- `GET /app/hdNN/mine` 各模块回 `compensation` / `totalAmount` / `verifyAmount` / `fees` —— 受害人账上的假余额 vs 第一道真收费(实测 ¥15,800 待补偿 / ¥499 验证费)
- `GET /app/hdNN/chat/messages` 常回全量群发脚本,`createdAt` 全部同一秒 = 广播而非真人对话;五个阶段常一一对应五个收费模块(税/反洗钱备案/公证)

## 坑

- token 短 TTL(见第 0 步),这是最常见的假阴性来源
- 小额被风控是常态,不是通道挂了,继续抬金额
- 聚合商收银台是第三方:只访问平台自己生成的链接,别拿 order_no 去遍历别单
- 提现单列表(`/app/withdraw-orders`)带 `walletKey` 参数但服务端按 token 绑定,多数无 IDOR,别反复试
- 下单即产生真实订单记录,金额用最小可过额度,不要真付款

## 关联

- 链上热钱包侧验证见 `wallet-exchange-fund-verification`(user-owned,未改)
- 前端协议/接口抽取见 `spa-js-api-mapping`、`frontend-js-api-recon`
