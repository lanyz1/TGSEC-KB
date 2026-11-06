# TRON 钱包工程 — 完整细节 (2026-09 实测)

配套演示脚本: `C:\Users\Administrator\Documents\tron_wallet_demo.py` (全链路手写+交叉验证)、`tron_signing_demo.py` (离线签名+验签闭环)、`tron_balance_scan.py` (派生+余额扫描器)。

## 1. 完整标准向量

| 向量 | 值 |
|------|-----|
| BIP39 seed ("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about") | `5eb00bbddcf069084889a8ab9155568165f5c453ccb85e70811aaed6f6da5fc19a5ac40b389cd370d086206dec8aa6c43daea6690f20ad3d8d48b2d2ce9e38e4` |
| BIP32 master (seed=`000102030405060708090a0b0c0d0e0f`) | priv `e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35` / chain `873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508` |
| keccak256("") | `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` (pycryptodome 验证) |
| 助记词 `route cruise then salt glare song surprise nurse tag leader grass height` | index0 → TRON `THTX3osuxM7Ryv5vnDpPutKNR8MtaE6EMR` / ETH `0x522397b73c2c6b717db4737c578cac07e71ff075`; index1 → TRON `TDakiaA4xdt5fJdDx9bKVKKWU3sf419RaW` |

## 2. TronGrid API 实测细节

- `/v1/accounts/{addr}` 响应结构: `data[0]` keys 含 `balance` (TRX sun), `trc20` (list of `{合约:余额}`), `trc10`, `account_resource`, `frozenV2`
- 未激活地址 → `{"data":[], "success":true}`; 活跃地址 → data 非空
- 实测真实地址解析: `TRvsvq7Gwkfm6QMEbayMk2rMPU42j7Lrjt` → TRX=1.703115, USDT=0.147764; `TRfpygriYPjLWUQ8PSUKXvBdKoVKqbR4M1` → TRX=1510.135226, USDT=113135.392272
- 找活跃地址技巧: `GET /v1/accounts/{USDT合约}/transactions/trc20?limit=3` 返回最近 USDT 转账的 from/to 地址 (合约地址视角 = 全网 USDT 转账流)
- 限流触发实测: 并发/高频 → `{"Error": "request rate exceeded the allowed_rps(3), and the query server is suspended for 1 s..."}` → sleep 1s+ 即恢复; 退避 5/10/15s 稳妥
- 生产建议: TronGrid API Key (developers.tron.network) 可提配额, 免费 3 rps 够扫描用

## 3. TRON 交易签名完整流程 (验证通过)

消息构造 (手写 protobuf 最小子集):
```
TransferContract:  owner_address=1(bytes), to_address=2(bytes), amount=3(int64 varint)
Any:               type_url=1(string), value=2(bytes)
Contract:          type=1(enum), parameter=2(Any)
Raw:               contract=1(repeated), ref_block_bytes=3, ref_block_hash=4, expiration=5, timestamp=8
ContractType enum: TransferContract=1, TriggerSmartContract=31
```

签名代码 (coincurve, 验证 PASS):
```python
msg_hash = hashlib.sha256(raw_data).digest()          # 消息 = sha256(raw_data), 不再二次哈希
cc_priv = CCPrivateKey.from_hex(priv_hex)
sig65 = cc_priv.sign_recoverable(msg_hash, hasher=None)  # 必须 hasher=None!
# 验签:
rec_pub = CCPublicKey.from_signature_and_message(sig65, msg_hash, hasher=None)
assert rec_pub.format(compressed=False) == derived_pub
```

- 65B 签名 = r(32)||s(32)||recid(1), 直接 hex 放 `signature: [hex]`
- 广播: `POST /wallet/broadcasttransaction` with `{raw_data: {...}, raw_data_hex: hex, signature: [hex]}`
- ref_block_bytes/hash 取链上最新块 (GET /wallet/getnowblock → blockID 前 3 字节/前 8 字节); 占位符会被节点拒绝但**不影响离线验签**

## 4. TRC20 (USDT) 转账签名要点

- 走 `TriggerSmartContract` (ContractType=31), 不是 TransferContract
- parameter.value: `contract_address` (hex), `data` = ABI 编码的 `transfer(address,uint256)`
- ABI 编码: `a9059cbb` (selector) + 32B address (24B padding + 20B 地址去 0x41) + 32B amount
- 需要 fee_limit (能量预算, 通常 10-30 TRX), 目标账户 0 TRX 转不动
- 签名/广播机制与 TRX 转账相同

## 5. 派生 + 扫描器核心代码模式

```python
# 派生 (bip_utils)
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
seed = Bip39SeedGenerator(mnemonic).Generate("")
ctx = (Bip44.FromSeed(seed, Bip44Coins.TRON)
         .Purpose().Coin().Account(acct)
         .Change(Bip44Changes.CHAIN_EXT).AddressIndex(idx))
addr = ctx.PublicKey().ToAddress()
priv = ctx.PrivateKey().Raw().ToBytes().hex()

# 单请求余额查询 (限速 + 429退避)
def query_account(addr, delay=0.4):
    d = api_get(f"/v1/accounts/{addr}", delay)
    if "_http_error" in d or "_error" in d: return {"trx": -1.0, "usdt": -1.0, "tokens": {}}
    data = d.get("data") or []
    if not data: return {"trx": 0.0, "usdt": 0.0, "tokens": {}}   # 未激活 = 0
    a = data[0]
    trx = (a.get("balance") or 0) / 1e6
    tokens = {c: int(b)/1e6 for e in (a.get("trc20") or []) for c, b in e.items()}
    return {"trx": trx, "usdt": tokens.get(USDT_CONTRACT, 0.0), "tokens": tokens}
```

base58check 解码 (自写, 必须剥离 checksum):
```python
def b58check_decode(s):
    n = 0
    for c in s: n = n*58 + ALPHABET.index(c)
    body = n.to_bytes((n.bit_length()+7)//8 or 1, 'big')
    pad = len(s) - len(s.lstrip('1'))
    raw = b'\x00'*pad + body
    payload, chk = raw[:-4], raw[-4:]
    assert hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] == chk
    return payload
```

## 6. 与弱 PRNG 研究的衔接

- 拿到助记词 → 扫描默认路径找钱: 这是「恢复自有资产」的标准做法
- 验证弱 PRNG 爆料: 先确认熵源 (逆向 APK 找 thread_rng/getrandom vs java.util.Random, 见 weak-rng-wallet-cracking), 再数学验证, 最后批量碰撞只对种子空间 ≤2^40 的目标有意义
- BIP39 校验和位数是爆料试金石: 12 词 = 4bit 校验和 (不是 16bit), 写错的爆料可信度大减
