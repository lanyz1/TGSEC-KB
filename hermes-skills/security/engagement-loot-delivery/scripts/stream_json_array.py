#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式迭代「单行巨型 JSON 数组」dump —— 几百 MB 写在一行的那种，json.load 会炸。

CLI:
    python3 stream_json_array.py <file.json>            # 数行 + 打印首条记录的键
    python3 stream_json_array.py <file.json> --keys     # 再列出所有出现过的键与频次
import:
    from stream_json_array import iter_array
    for obj in iter_array(path):
        ...
"""
import collections, json, sys


def iter_array(path, chunk=1 << 22):
    """按需产出数组元素；内存占用与「单条记录」同量级，与文件大小无关。"""
    dec = json.JSONDecoder()
    buf, pos, started = "", 0, False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            buf += data
            if not started:
                i = buf.find("[")
                if i == -1:
                    buf = ""
                    continue
                pos, started = i + 1, True
            while True:
                while pos < len(buf) and buf[pos] in " \t\r\n,":
                    pos += 1
                if pos >= len(buf):
                    break
                try:
                    obj, end = dec.raw_decode(buf, pos)
                except ValueError:
                    break          # 本条还没读全，等下一块
                yield obj
                pos = end
            buf, pos = buf[pos:], 0   # 丢弃已消费部分，别涨 buffer


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    want_keys = "--keys" in sys.argv
    keys = collections.Counter()
    n, first = 0, None
    for obj in iter_array(path):
        n += 1
        if first is None:
            first = obj
        if want_keys and isinstance(obj, dict):
            keys.update(obj.keys())
    print("记录数: %s" % format(n, ","))
    if isinstance(first, dict):
        print("首条记录键: %s" % list(first.keys()))
    for k, c in keys.most_common():
        print("   %-28s 出现 %s 次" % (k, format(c, ",")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
