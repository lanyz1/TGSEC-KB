#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_host_func.py — VA → 宿主函数一步定位(未剥离 Go 二进制)

用法:
    go tool nm -size -sort address <bin> > symtab.txt
    python find_host_func.py symtab.txt 0x114f8df 0x1151f86 0x114b2d8

symtab 行须含:16位hex地址 + "F .text" + 16位hex大小 + 函数名
(即 `go tool nm -size -sort address` 导出形态;解析出 0 行时先肉眼比对头几行,按需改 LINE 正则)。
输出:每个输入地址命中的函数 [start, start+size) 与名字;未命中提示核对 load delta。
用途:xref 命中的引用地址/调用点 → 立刻知道属于哪个函数(谁发射了这句错误、谁调用了它)。
"""
import re
import sys

LINE = re.compile(r'^([0-9a-f]{16})\s+\S*\s*F\s+\.text\s+([0-9a-f]{16})\s+(\S.*?)\s*$')


def load_rows(path):
    rows = []
    for line in open(path, encoding='utf-8', errors='replace'):
        m = LINE.match(line)
        if m:
            rows.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3)))
    rows.sort()
    return rows


def find_host(rows, target):
    for addr, size, name in rows:
        if addr <= target < addr + size:
            return (addr, size, name)
        if addr > target:
            break
    return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    rows = load_rows(sys.argv[1])
    print('loaded %d funcs from %s' % (len(rows), sys.argv[1]))
    for arg in sys.argv[2:]:
        t = int(arg, 16)
        h = find_host(rows, t)
        if h:
            print('%#x -> %s  [start=%#x size=%#x]' % (t, h[2], h[0], h[1]))
        else:
            print('%#x -> NOT FOUND (核对 load delta / 地址)' % t)


if __name__ == '__main__':
    main()
