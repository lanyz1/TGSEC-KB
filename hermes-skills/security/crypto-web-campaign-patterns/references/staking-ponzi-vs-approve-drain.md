# 真质押盘 vs 授权盗U：链上定性手册

回答「**这个是授权盗U的站吗**」的完整判据。适用于任何带质押/挖矿/理财的链上盘。
2026-09-23 vvveco.io（Base 链 VVV 假 Venice 质押盘）沉淀。

## 0. 先分成三档，别二元判断

用户问「是不是盗U」时，答案有三个可能，**只有第③档才按「停止+删除」处理**：

| 档 | 形态 | 处置 |
|----|------|------|
| ① | **真 approve-drainer**（授权盗U） | 继续打：找 spender/owner 钥 |
| ② | **假盘但用户自愿存入**（存款即变现庞氏 / honeypot staking） | **不是盗U，但仍是对抗目标**：交付资金流向 + 定性报告 |
| ③ | **合法生意被误判**（例：piu = OKX 拉新 affiliate） | 立即停手 + 全删 |

**铁律：非盗U ≠ 合法生意。** ②③ 混为一谈会把吃本金的盘当正经生意放掉。
判据落在「币是否离开用户控制且进了运营方口袋」+「机制是否需要用户被骗签恶意授权」。

## 1. 授权盗U 的硬判据（缺一则降档）

1. `approve` 的 spender 是**恶意 EOA / 攻击者合约**，不是业务合约
2. 存在「拿到 MAX 授权后 `transferFrom` 清空**钱包全部余额**」的路径
3. 合约里有 `sweep` / `rescue` / `drain` / 任意额 `transferFrom` 函数（**多处** transferFrom）
4. 没有真实业务逻辑与真实收益发放

`grep -n 'transferFrom\|safeTransferFrom\|transfer(' <Staking>.sol` —— **只有 1 处、且在 `stake()` 内**＝不是 drainer。

## 2. ② 存款即变现庞氏 的硬判据

关键：**用户存进去的币当场被卖掉，钱进运营方钱包**，但走的是用户自愿调用的合约函数。

### 2.1 读合约 `stake()` 的资金去向（决定性）

```solidity
// 典型掠夺形态（vvveco 实测）
require(vvvToken.transferFrom(msg.sender, address(treasury), vvvAmount));
treasury.receiveAndConvert(msg.sender, vvvAmount);   // ← 卖掉 + 打给 projectWallet
```

合约头注释常**自己写明**流向：`STAKE: user VVV ──transferFrom──▶ Treasury ──swap──▶ ETH ──▶ projectWallet`。
先通读合约顶部注释，比读代码快。

### 2.2 链上验证「本金不留在合约」

| 检查 | 结论 |
|------|------|
| staking 合约的 VVV `balanceOf` = 0 | 本金不在合约 → 被转走 |
| treasury 的 VVV/ETH ≈ 0 | 只做中转，不托管 |
| `treasury()` / `payout()` / `projectWallet()` 读出的地址 | 追资金终点的三个关键地址 |
| projectWallet 是 EOA（`eth_getCode` 空）+ 有大额 ETH | **运营方热钱包收了变现款** |

### 2.3 追变现流水（Alchemy `alchemy_getAssetTransfers`，实测可用）

`eth_getLogs` 从 `fromBlock: 0x0` 全量扫常被拒（Alchemy 400 / 区间限制）。
**改用 `alchemy_getAssetTransfers`**（能一次拿到 external + internal + erc20 全史，含 swap 出来的 ETH 内部转账）：

```python
j = rpc('alchemy_getAssetTransfers', [{
    'fromBlock':'0x0','toBlock':'latest','maxCount':'0x3e8',
    'order':'desc','excludeZeroValue':True,'withMetadata':True,
    'fromAddress': TREASURY, 'category': ['erc20'],
    'contractAddresses': [VVV],
}])
# → 累加 value 得「累计卖出多少 VVV」
# category=['internal'] + toAddress=projectWallet → 「收到多少 ETH」（swap 收益）
```
分页用返回的 `pageKey`。

### 2.4 事件计数（决定性：这盘还在兑付吗）

**Alchemy 全量 `eth_getLogs` 会被拒；用 Blockscout v1 Etherscan 兼容口（免 key，实测可用）**：

```bash
curl -s "https://base.blockscout.com/api?module=logs&action=getLogs\
&address=<STAKING>&topic0=<keccak(sig)>&fromBlock=0&toBlock=latest"
```

topic0 自己算（`keccak256(sig)`）。计这几个：

| 事件 | 含义 |
|------|------|
| `PrincipalWithdrawn(address,uint256,uint256)` | **用户真拿回过本金** → 还在兑付，不是已跑路 |
| `RewardClaimed(address,uint256)` | 收益真发 |
| `Staked(...)` | 存款笔数（**签名要先从 ABI 核**，猜错会返回 0，别当「无人存款」） |
| payout: `PrincipalPaid` / `RewardPaid` / `AdminPaid` | 出款面 |

**注意**：Blockscout v2 `/addresses/{addr}/transactions` 可能回 **422**；`/api?module=logs&action=getLogs`（v1）可用。

### 2.5 价格预言机 vs 真实市价（放大倍数）

合约的 `getLatestPrice()` 常是**自有预言机**，估值可虚高。核法：

- `eth_call` 合约 `getLatestPrice()` → 除 1e18 得它自报的币价
- 路由 `getAmountsOut(1e18 <TOKEN>, [TOKEN, WETH])` → 反推真实市场价
- 对比 CoinGecko / 代币在交易所的真实价

vvveco 实测：合约报价 **$29.7**，VVV 真实市价 **$15.06** → 平台账面质押金额（$43,046）**虚高一倍**。
汇报时**必须两栏写**：平台口径 vs 真实口径。

### 2.6 兑付能力缺口（运营风险量化）

```
账面质押总额（平台口径）          $43,046
payout 合约实际持有 ETH            0.709 ETH   ← 唯一兑付来源
→ 兑付能力差一个数量级
```

再看 payout 的 ETH **从哪来**（`toAddress=payout, category=['external','internal']` 的 from 聚合）：
若来自运营方 EOA 而非营收 → 就是**靠回填撑着的庞氏**。

## 3. 结论口径模板

```
不是授权盗U（无 approve 清空机制，全合约仅 1 处 transferFrom，用户确实能赎回 22 笔）
但是 <存款即变现> 庞氏：真代币 + 真合约 + 真 DEX 路由，
机制是「存款即变现进运营方」，靠运营方持续回填 ETH 维持兑付。
目前仍在兑付（22 笔本金赎回 + 1000+ 笔收益），不是已跑路。
比 drainer 更隐蔽：不需要用户签恶意授权，主动存进去的币当场被卖。
```

## 4. Pitfalls

- **「没有恶意 approve」≠「安全」**。本类盘的 `approve` 是给业务合约的常规 MAX 授权，判据在
  资金**流向**，不在 `approve` 是否存在。
- **用户报的「全球质押金额」是前端灌水**：`/api/global-stats` 常把 `real` 与 `config.base*` 分开返回，
  `base*` 是**展示用基数**（vvveco：真实 $43,046 / 88 人，基数 174,630 / 1512 人）。取 `real`。
- **猜事件签名会得 0 条**，别据此下「无人使用」的结论——先去 ABI / 源码核签名再查。
- 合约源码在项目 GitHub 仓里时，**先 `git clone` 读 `.sol`**，比逆向字节码快一个量级。
- 拿不到 owner/spender 钥时**不要**叙述「可归集」；`BLOCKED_NO_KEY` 如实写。
