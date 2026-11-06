#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
java.util.Random 可预测性验证 POC
验证: ① 48 位种子 LCG 特性 ② 从两个连续 nextInt(32) 输出反推种子(O(2^16))
用途: 评估「某 Android 钱包/软件用 java.util.Random 生成助记词/私钥」类爆料的技术真实性
参考: security-case-research/references/prng-claim-verification.md(imToken 案例)

Java Random 内部:
  seed = (seed * 0x5DEECE66D + 0xB) & ((1<<48)-1)
  next(32) 返回 seed >> 16 的高 32 位
"""
import random

MULT = 0x5DEECE66D
ADD  = 0xB
MASK48 = (1 << 48) - 1

def java_next(bits, seed):
    seed = (seed * MULT + ADD) & MASK48
    return seed, seed >> (48 - bits)

def recover_seed(out1, out2):
    """从两个连续 next(32) 输出反推种子。O(2^16)。"""
    inv = pow(MULT, -1, 1 << 48)
    for low16 in range(1 << 16):
        newseed = (out1 << 16) | low16
        oldseed = ((newseed - ADD) * inv) & MASK48
        s_tmp, v1 = java_next(32, oldseed)
        if v1 == out1:
            s_tmp2, v2 = java_next(32, s_tmp)
            if v2 == out2:
                return oldseed
    return None

def main():
    print("=" * 62)
    print("java.util.Random 可预测性验证 POC")
    print("=" * 62)
    print(f"\n[1] 种子空间: 2^48 = {2**48:,} ≈ 2.8e14")

    true_seed = 0x123456789ABC
    s = true_seed
    outputs = []
    for _ in range(4):
        s, v = java_next(32, s)
        outputs.append(v)
    print(f"\n[2] 真种子:   0x{true_seed:012X}")
    print(f"    连续输出: {outputs}")

    seed_recovered = recover_seed(outputs[0], outputs[1])
    print(f"    反推种子: 0x{seed_recovered:012X} (匹配: {seed_recovered == true_seed})")
    print(f"    复杂度:   O(2^16) = 65,536 次 = 毫秒级")

    ok = 0
    for i in range(10):
        ts = random.getrandbits(48)
        s = ts
        o = []
        for _ in range(2):
            s, v = java_next(32, s)
            o.append(v)
        if recover_seed(o[0], o[1]) == ts:
            ok += 1
    print(f"\n[3] 随机种子 10 轮反推: {ok}/10 成功")

    print(f"\n[4] 若助记词 128 位熵实际只来自 48 位种子:")
    for speed in [1e6, 1e7, 1e8]:
        hours = 2**48 / speed / 3600
        print(f"    派生速度 {speed:.0e}/s → {hours:.0f} 小时 ({hours/24:.1f} 天)")

    print(f"\n[5] 结论: 观测 2 个连续输出 → 秒解种子;仅知地址 → 2^48 暴力(数小时~数天)")
    print(f"    任何用 java.util.Random 生成助记词的钱包都是致命缺陷。")

if __name__ == "__main__":
    main()
