# 授权盗 U vs 固定 USDT 收款（口头定性用）

| | 授权盗 U | 固定地址 / 发卡 / 筛号 / 能量 |
|--|----------|------------------------------|
| 钱包 | connect + approve/increaseApproval MAX | 不需要，或只填公开地址 |
| 配置 | `/payment-config`、spender | 地址写死 JS / 下单返回 / 后台 config |
| 链上 | allowance → transferFrom | 普通 transfer 入热钱包 |
| 文案 | 授权、授权挖矿、无限额度 | 转账到该地址、易支付、epusdt、金币充值 |

**快速否决盗 U：** 无 payment-config、无 approve、有 bill/order/USDT 复制地址。

**WP 云控介绍页：** 不是运行时；跟 `order.*` / `data.*` / `appfilter` / TG。
