---
name: tron-wallet-engineering
description: "TRON/波场钱包工程: 派生/签名/余额扫描。触发: TRON, 波场, USDT TRC20。"
---

# TRON 钱包工程 (BIP39/BIP44 + 签名 + TronGrid)

波场链钱包的助记词/私钥/地址全链路、离线交易签名、链上余额批量扫描。2026-09 全链路实测验证 (标准向量 PASS + 真实链上数据解析确认)。

## 全链路

```
熵 128bit (CSPRNG) → BIP39 12词 → PBKDF2-HMAC-SHA512("mnemonic"+pass, 2048) → 64B seed
→ HMAC-SHA512("Bitcoin seed", seed) → master → CKDpriv 沿 m/44'/195'/0'/0/0 → 私钥
→ secp256k1 未压缩公钥 → keccak256(pub[1:])[12:] → 0x41 前缀 → base58check → T开头地址
```

- 12词 = 128bit 熵 + **4bit** 校验和 (CS=ENT/32; 15/18/21/24 词 = 160/192/224/256 + 5/6/7/8)。随机拼 12 词通过校验和 = 1/16
- **TRON coin type = 195** (ETH=60); 同助记词/私钥跨链通用, 只有地址编码链相关 — 导入钱包选错链 = 空钱包
- 派生规律: 同一助记词 index 递增 → 一串地址 (钱包「刷新收款地址」的底层逻辑); 微变/换序 → 校验和拒绝或雪崩

## 标准向量 (验证实现用)

| 向量 | 值 |
|------|-----|
| BIP39 seed ("abandon...about") | `5eb00bbd...e38e4` (见 references 全值) |
| BIP32 master (seed=0001...0e0f) | priv `e8f32e72...`, chain `873dff81...` |
| keccak256("") | `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` |
| `route cruise then salt glare song surprise nurse tag leader grass height` | index0 → TRON `THTX3osuxM7Ryv5vnDpPutKNR8MtaE6EMR` / ETH `0x522397b7...` |

## TronGrid API 坑 (实测)

| 坑 | 细节 |
|----|------|
| POST 端点只要 hex | `/wallet/triggerconstantcontract` `/wallet/getaccount` 传 base58 → `JsonFormat$ParseException: INVALID hex String`; 传 `0x41...` hex (42 字符) |
| REST 端点收 base58 | `/v1/accounts/{addr}` 直接收 base58, 最省事 |
| 免费限流 3 rps | 超限: `request rate exceeded the allowed_rps(3)... suspended` → 串行 + sleep + 429 退避 5/10/15s |
| `trc20` 字段 | `/v1/accounts/{addr}` → `data[0].trc20 = [{合约:余额sun}]` **一次拿全部 TRC20**, 比 balanceOf 快一倍 |
| 未激活地址 | `data: []` = 余额 0 (非查询失败); 用 `-1.0` 区分查询失败 |
| base58check 解码 | 必须剥离尾 4B checksum, 否则 25B 地址 → `CONTRACT_VALIDATE_ERROR` |
| Tronscan 公开端点 | 2026-09 大多 404/空/需认证 (`/api/token/holders` 等), 别依赖 |

USDT TRC20 主网合约: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`; 1 TRX = 1e6 SUN.

## 离线签名

- 消息 = `sha256(raw_data protobuf)` — **不再二次哈希**。coincurve `sign_recoverable(msg, hasher=None)`; 默认 hasher=sha256 会双重哈希 → 验签 FAIL
- 签名 65B = `r(32)||s(32)||recid(1)`; 验签 `PublicKey.from_signature_and_message(sig, msg, hasher=None)` 恢复公钥比对
- 广播 payload `{raw_data, raw_data_hex, signature:[hex]}` → POST `/wallet/broadcasttransaction`; **ref_block 必须真实最新块**, 占位符节点拒绝
- protobuf 字段与 TRC20 签名细节: 见 `references/tron-wallet-engineering.md`

## 手续费 (拿助记词 ≠ 立刻能提)

| 转账类型 | 消耗 | 说明 |
|---------|------|------|
| 转 TRX | 带宽 Bandwidth | 每日免费额度, 超额质押/燃烧 |
| 转 USDT TRC20 | 能量 Energy | 免费很少, ~32 TRX/次; **目标账户 0 TRX 时 USDT 转不走** — 需先注入 TRX 垫手续费 |

## bip_utils 2.x 陷阱

- `Secp256k1` 是实例不是类 → `Secp256k1PrivateKey.FromBytes(pk).PublicKey().RawCompressed/Uncompressed().ToBytes()`
- 无 Keccak256Digest → `pip install pycryptodome`, `Crypto.Hash.keccak.new(digest_bits=256)` (原始 Keccak; `Sha3_256` 是 NIST SHA3 **不可用**)
- `Base58Encoder` 无 Decode → 自写 base58check decode (含 checksum 剥离 + 前导 1 padding)

## 派生+余额扫描器

完整工具: `C:\Users\Administrator\Documents\tron_balance_scan.py` — 助记词 → account×index 批量派生 → 单请求查 TRX+全部 TRC20 → 有余额附私钥 → JSON 落盘。
用法: `python tron_balance_scan.py --mnemonic "..." --accounts 3 --indexes 20 [--json out.json] [--quiet]`
核心查询模式 + 派生代码: 见 references。

## 安全边界

扫描他人助记词 = 盗窃 (Profanity/Coldcard 攻击者已追责); 工具用于恢复自有资产/授权研究/弱 PRNG 钱包验证 (配合 prng-secret-recovery / weak-rng-wallet-cracking)。CSPRNG 主流钱包批量碰撞无效 (2^128)。

## 参考文件

- `references/tron-wallet-engineering.md` — 完整向量值/protobuf 编码/签名代码模式/扫描器核心函数
