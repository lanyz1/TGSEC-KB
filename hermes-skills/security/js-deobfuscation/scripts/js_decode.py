#!/usr/bin/env python3
"""obfuscator.io 自定义字母表 Base64 + URI 解码器(Python 复刻,已与 Node 交叉验证 200/200)。

用法:
  python3 js_decode.py arr_rotated.json 0x17e3 0x220e 1234
  # 参数为「调用实参坐标」,内部按 arr[param - OFFSET] 取值(默认 OFFSET=0x128,按目标解码器里
  # 的 `_0x220658=_0x220658-0x128` 调整)

注意:
  - ALPHA 必须照抄目标解码器里的字母表 (实测变体: 小写在前)
  - 批量使用前先与 Node 真执行结果交叉验证 >=200 样本
"""
import json, sys

ALPHA = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/='
OFFSET = 0x128

def js_decode(s: str) -> str:
    out = bytearray()
    a = 0
    i = 0
    for ch in s:
        b = ALPHA.find(ch)
        if b == -1:
            continue
        if i % 4 != 0:
            a = a * 64 + b
        else:
            a = b
        if i % 4 != 0:
            i_new = i + 1
            shift = (-2 * i_new) & 6
            out.append((a >> shift) & 0xFF)
        i += 1
    return bytes(out).decode('utf-8', 'replace')

def dec(arr, param, offset=OFFSET):
    return js_decode(arr[param - offset])

if __name__ == '__main__':
    arr = json.load(open(sys.argv[1]))
    print('array len:', len(arr))
    for p in sys.argv[2:]:
        v = int(p, 16) if p.lower().startswith('0x') else int(p)
        print(p, '=>', repr(dec(arr, v)))
