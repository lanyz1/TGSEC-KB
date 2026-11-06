#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
java.util.Random 种子反推 POC
从两个连续 nextInt(32) 输出反推 48 位种子,复杂度 O(2^16)(毫秒级)。
验证任何「XX 用 java.util.Random 生成密钥/助记词」爆料的技术真实性。
实测: 10/10 随机种子反推成功。
"""
import random

MULT = 0x5DEECE66D
ADD = 0xB
MASK48 = (1 << 48) - 1

def java_next(seed, bits=32):
    seed = (seed * MULT + ADD) & MASK48
    return seed, seed >> (48 - bits)

def recover_seed(out1, out2):
    """两个连续 next(32) 输出 -> 种子。枚举 newseed 低16位,反解 oldseed,验证 out2。"""
    inv = pow(MULT, -1, 1 << 48)
    for low16 in range(1 << 16):
        newseed = (out1 << 16) | low16
        oldseed = ((newseed - ADD) * inv) & MASK48
        s_tmp, v1 = java_next(oldseed, 32)
        if v1 == out1:
            s_tmp2, v2 = java_next(s_tmp, 32)
            if v2 == out2:
                return oldseed
    return None

def main():
    print("java.util.Random 种子反推验证 POC")
    print("种子空间: 2^48 ≈ 2.8e14")
    # 演示: 确定种子
    true_seed = 0x123456789ABC
    s = true_seed
    outs = []
    for _ in range(4):
        s, v = java_next(s, 32)
        outs.append(v)
    print(f"真种子: 0x{true_seed:012X}")
    print(f"连续输出: {outs}")
    r = recover_seed(outs[0], outs[1])
    print(f"反推种子: 0x{r:012X} (匹配: {r == true_seed})")
    # 随机种子 10 轮
    ok = 0
    for _ in range(10):
        ts = random.getrandbits(48)
        s = ts
        o = []
        for _ in range(2):
            s, v = java_next(s, 32)
            o.append(v)
        if recover_seed(o[0], o[1]) == ts:
            ok += 1
    print(f"随机种子 10 轮: {ok}/10 成功")

if __name__ == "__main__":
    main()
