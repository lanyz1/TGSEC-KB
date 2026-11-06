# USDT 收款形态分类：固定地址 vs 授权盗 U（及易混壳）

用户常问「是不是授权盗 U」。**先分类再选技能**；口头回答用 1 屏对照表。

| | **授权盗 U / heyue** | **固定地址收款** | **发卡 faka + 链上付** | **能量租用 MiniApp** |
|--|----------------------|------------------|------------------------|----------------------|
| 前端 | 连钱包 + `approve`/`increaseApproval` | 展示地址/二维码 | 下单页 email+payway | 填 TRON 地址，不连钱包 |
| 配置 | `/payment-config`、spender、MAX_UINT | JS 写死（可 zlib） | 易支付/epusdt 商户 | `/config` `/swap` 下发地址 |
| 链上 | allowance → `transferFrom`/heyue | 普通 `transfer` 入账 | 用户转 USDT/TRX 到商户址 | 同左 + DelegateResource 能量 |
| 技能 | defi / caishen | 本页 + jbridgek | `dujiaoka-epusdt-faka.md` | `tron-energy-miniapp.md` |
| 硬资产 | owner/spender 钥 | 收款 EOA 钥（常无） | 卡密+支付 key+admin | 热钱包+bot token |
| 否决信号 | 有 approve | 无 approve | 无 approve、有 bill/订单 | 无 approve、要 TG initData |

**快速否决授权盗 U：** 无 `/payment-config`、无 `approve`/`increaseApproval`、支付文案是「转账到该地址」/支付宝/易支付/epusdt → **不是**盗 U。

## 固定地址站快速指纹（jbridgek 类）

- GitHub Pages + CF；小红书号/社账号批发 SEO
- 详情页：邮箱 + 数量 + USDT-TRC20/ERC20/BEP20/Solana
- JS 强混淆 + `debugger` + 域名锁；配置在 **zlib+base64**（`eNr...`）里
- 解压后字段例：
  - EVM：`0x476A5A57D15b2c4254a7306f9d83e14D294F2546`
  - TRX：`TUoJWCV9HYykEg6RyKU2Z6zJzM8cRMZgex`
  - SOL：`6L6QnotQDQ5CvfqFMHhzicrydyyro7nysFxtzh75kmf5`
- 无 `/api` 下单；15 分钟倒计时模态框纯前端
- **不要**当 approve 盘扫 payment-config；**不要**指望 getshell

## 解压套路

```python
# 从 bundle 抽 eNr... → b64decode → zlib.decompress(raw, 15)
# 再 json.loads 或扫 0x/T/Sol 地址
```

## 与 nowpayments 真商店

`crypto-marketplace-pentest.md`：有真实 `/api/checkout` + 链上确认发货。  
固定地址号商站通常 **无后端订单 API**，更接近静态收款页。
