<!-- archived from /root/.hermes/skills/security/prng-secret-recovery/SKILL.md on 2026-10-21 -->

---
name: prng-secret-recovery
description: "验证弱PRNG助记词/密钥漏洞爆料并构建恢复工具时使用。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/prng-secret-recovery`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/prng-secret-recovery/…')`，不要相对 `references/legacy/` 解析。

# 弱 PRNG 密钥/助记词恢复与爆料验证

针对「XX 钱包/软件用弱伪随机数生成器(PRNG)生成助记词/私钥/卡密,可被暴力破解」这类爆料的**技术验证 + 恢复工具构建**方法论。核心三件事:①源码取证核实爆料 ②数学验证 PRNG 可预测性 ③构建种子枚举/助记词补齐工具。

## 何时使用

- 用户发来「XX 钱包爆设计缺陷: 助记词可暴力破解」「内部留后手/被搞走几百万」类爆料要求研究
- 需要验证某软件是否用 `java.util.Random` / `rand()` / 时间种子等弱 PRNG 生成安全密钥
- 需要从已知地址/部分助记词/部分种子恢复助记词(找回丢失钱包)
- 任何「128 位熵实际只有 N 位」的熵降级指控

## 工作流

1. **技术原理先验证(数学)**: 复刻目标 PRNG 算法,证明可预测性。java.util.Random 是 LCG:
   ```python
   MULT=0x5DEECE66D; ADD=0xB; MASK48=(1<<48)-1
   def java_next(seed,bits=32):
       seed=(seed*MULT+ADD)&MASK48
       return seed, seed>>(48-bits)
   def java_random_fill(seed,nbytes=16):  # 模拟 nextBytes()
       out=bytearray()
       while len(out)<nbytes:
           seed,v=java_next(seed,32); out.extend(v.to_bytes(4,'big'))
       return bytes(out[:nbytes])
   ```
   **关键**: 从两个连续 nextInt(32) 输出反推 48 位种子只需 O(2^16) 枚举(枚举 newseed 低16位→反解 oldseed→验证下一输出),毫秒级。见 `scripts/java_lcg_break.py`。

2. **BIP39 细节核对(爆料常记错)**: CS = ENT/32。12 词 = 128 位熵 + **4 位**校验和(不是 16!);24 词 = 256 + 8。爆料的校验和位数错了 = 可信度打折的强信号。

3. **源码取证(核实"用了什么 RNG")**:
   - GitHub 搜官方组织: `api.github.com/orgs/<org>/repos` → 找钱包核心仓库
   - 递归文件树: `api.github.com/repos/<repo>/git/trees/<branch>?recursive=1` → 搜 mnemonic/rand/bip39/hdwallet
   - 抓关键源码: `raw.githubusercontent.com/...`(免费,无需 token)
   - 依赖确认: 查 Cargo.toml/package.json 的 rand/bip39 版本
   - **crate 源码下载验证**: `crates.io/api/v1/crates/<name>/<ver>/download` → tar 解包看 `gen_random_bytes` 用的什么
   - Rust 生态判定: `rand::thread_rng()` = ChaCha12 CSPRNG(OS 熵源),**不是** 48 位 LCG;`tiny-bip39`/`bip39` crate 内部走 thread_rng → 128 位全熵,不可爆

4. **公开渠道佐证**: Google News RSS 搜「品牌 + vulnerability/hack」→ 零条相关 = 无公开 CVE,爆料大概率是传闻/钓鱼误归因(钓鱼才是钱包被盗主因,不是 PRNG 破解)。

5. **构建恢复工具**(见 `references/mnemonic-crack-tooling.md`):
   - 模式 A 补齐缺失词: `--mnemonic "... ?"` → BIP39 校验和过滤 + 地址比对。缺 1 词 0.4s,缺 2 词分钟级 ✅
   - 模式 B 种子枚举: 枚举 java.util.Random 种子 → 熵 → 助记词 → 派生地址比对(小空间可用)
   - 模式 C 观测输出反推: 2 个连续输出 → O(2^16) 毫秒级 ✅✅ 最优
   - 地址派生加速: `hashlib.pbkdf2_hmac('sha512', ...)`(OpenSSL C)+ `coincurve`(secp256k1 C)+ `eth_hash.auto.keccak`;依赖 `pip install mnemonic bip-utils coincurve eth-account`

## 可行性边界(必须诚实,别画大饼)

| 场景 | 候选数 | 耗时 | 判定 |
|------|--------|------|------|
| 缺 1 词 | 2,048 | 0.4s | ✅ |
| 缺 2 词 | 4.2M | 分钟级 | ✅ |
| 观测 2 输出反推 | 65K | 毫秒级 | ✅✅ |
| 种子低 32 位已知 | 65K | 秒级 | ✅ |
| 1 小时 nanoTime 窗口 | 3.6e12 | CPU 数百年 | ❌ 需 GPU |
| 全空间 2^48 | 2.8e14 | CPU 千年 | ❌ 需 ASIC/FPGA |

- 纯 Python 速率实测: 单进程 ~350-750 候选/秒(含完整 BIP39+PBKDF2+BIP44),8 进程 ~2,800/秒
- 爆料说「2^48 数小时」= GPU 集群/FPGA 量级(RTX4090 单卡 ~1e8-1e9/s ≈ 3 天;多卡数小时),不是普通电脑
- **真正实用路径**: 补齐缺失词 / 观测输出反推 / 种子部分已知。全空间暴力 = 国家级硬件能力,诚实告知

## Pitfalls

- **f-string 三层引号会崩**: 状态打印用 `"%d" % var` 或先拼字符串,别在 f-string 里嵌 `[`/`]` 三元表达式
- **argparse subparsers `required=True` 参数**: 老 Python 不支持,用 `sub.required=True` 单独赋值
- **函数参数顺序**: 重写脚本时保持 `java_next(seed, bits)` 签名一致,调用别传反(48-32=16 负移位 = 参数顺序错)
- **纯 Python 枚举大空间必超时**: 1e12 级循环 × 每次完整派生,execute_code 5 分钟必被杀;用小窗口/分片演示正确性,再外推速率
- **助记词校验和过滤前置**: 无效组合(1/256)先被 mnemonic 库抛异常过滤,再派生地址,省大量计算
- **自检用例**: `"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"` → ETH `0x9858EfFD232B4033E47d90003D41EC34EcaEda94`(BIP39 标准测试向量),派生链通了再跑真实目标
- **Google News RSS 是免费免 token 的事件验证渠道**,新闻 URL 别猜(TechCrunch/BleepingComputer 猜 URL 全 404)

## 2026 新增: V8 Math.random (xorshift128+) 状态恢复攻击 — Ill Bloom 案例

**真实事件 (2026-07 Coinspect 披露)**: 5 个钱包 App 用 `CryptoJS.lib.WordArray.random()` 生成助记词,被盗 $5M+。CryptoJS 3.x 该函数内部 = `(Math.random() * 0x100000000) | 0` 逐词生成 → 熵来自 V8 的 Math.random。

**攻击链 (已验证, 见 C:\Users\Administrator\Documents\ill_bloom_full_chain.py)**:
```
观察 4 个连续 Math.random() double (高53位) → z3 恢复 xorshift128+ 128位状态
  → 回溯到助记词生成时刻 → 重建熵 → BIP39 助记词 → BIP44 TRON/ETH 地址 → 资产可控
```

**V8 xorshift128+ 关键细节(踩坑记录)**:
- 状态 (s0,s1) 64bit×2;推进: `s0' = s1; s1' = s0 ^ (s0<<23) ^ s1 ^ (s1>>17) ^ (s1>>26)`
- **输出 = 推进后新状态之和** `s0' + s1'`(不是旧状态!)——回溯时输出 = 当前状态和
- double = (out >> 11) * 2^-53(只暴露高 53 位,低 11 位未知,z3 用 BitVec 处理)
- z3 求解: 4 个输出约束 (LShR(out,11) == high53), ~36ms
- 逆转移: `prev_s1 = cur_s0`; `prev_s0` 解 `x ^ (x<<23) = R` 按 bit 递推
- 攻击场景: 恶意 iframe/同进程脚本调用 Math.random() 探测(2015 年公开 PoC 原理,同进程共享状态)

**CryptoJS 判定**: JS bundle 搜 `WordArray.random` / `lib.WordArray` / `cryptojs` + 熵路径调用 = 中招。
四款主流 (imToken/TP/Trust/MetaMask) 实测 0 命中,全走 getRandomValues/thread_rng。

## 参考文件

- `references/mnemonic-crack-tooling.md` — 三类破解器(mnemonic_cracker.py / fast 版 / rng_time_window_crack.py)的完整代码模式、地址派生加速链、imToken 案例验证结论
- `references/weak-prng-imtoken-case.md` — imToken 爆料完整验证: 技术原理成立但指控被 Rust thread_rng 源码证伪;BIP39 校验和错误;钓鱼才是主因
- `scripts/java_lcg_break.py` — java.util.Random 种子反推 POC(从 2 个连续输出 O(2^16) 反推,10/10 轮验证)
