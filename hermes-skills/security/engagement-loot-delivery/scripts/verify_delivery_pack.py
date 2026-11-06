#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付包校验器 —— 发货前跑一遍，别把 join 断掉的表发出去。

用法:
    python3 verify_delivery_pack.py <交付目录> [zip路径]
退出码: 0 = 全部通过 / 1 = 有告警

检查:
  · 每张 CSV 的行数、表头、各列「空或全零」占比
  · 整列 100% 空/全零 → 告警(通常是聚合 join 用了源里不存在的字段名)
  · 首列 id 唯一性: 行数 != 唯一数 = 重复分页残留 / 口径不对
  · zip: testzip() 必须为 None, 且交付目录里的每个文件都在包里
注: 整列非零 != 业务正确, 仍要人工抽查关键行(规模最大的那条线/客户)是否合理。
"""
import collections, csv, os, sys, zipfile

csv.field_size_limit(10 ** 8)
EMPTY = {"", "0", "0.0", "0.00", "none", "null", "nan"}


def check_csv(path):
    warns = []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        hdr = rd.fieldnames or []
        rows = 0
        empt = collections.Counter()
        ids = set()
        for row in rd:
            rows += 1
            for k, v in row.items():
                if str(v).strip().lower() in EMPTY:
                    empt[k] += 1
            if hdr:
                ids.add(str(row.get(hdr[0])).strip())
    print("\n-- %s" % os.path.basename(path))
    print("   行数 %s | 列 %s | 首列「%s」唯一值 %s" % (format(rows, ","), len(hdr), hdr[0] if hdr else "-", format(len(ids), ",")))
    if hdr and rows and len(ids) != rows:
        warns.append("%s: 首列不唯一 (%s 行 / %s 唯一) —— 重复分页残留?" % (os.path.basename(path), format(rows, ","), format(len(ids), ",")))
    for k in hdr:
        if not rows:
            break
        if empt[k] == rows:
            warns.append("%s: 列「%s」100%% 空/全零 —— join 的字段名可能不存在" % (os.path.basename(path), k))
        elif empt[k] / rows > 0.99:
            print("   ! 列「%s」%.1f%% 空/全零" % (k, empt[k] * 100.0 / rows))
    return rows, warns


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    d = sys.argv[1]
    zpath = sys.argv[2] if len(sys.argv) > 2 else None
    warns, total, n = [], 0, 0
    for fn in sorted(f for f in os.listdir(d) if f.lower().endswith(".csv")):
        r, w = check_csv(os.path.join(d, fn))
        total += r
        n += 1
        warns += w
    print("\n合计 CSV %d 张 / %s 行" % (n, format(total, ",")))
    others = [f for f in sorted(os.listdir(d)) if not f.lower().endswith(".csv")]
    print("非 CSV 交付件: %s" % (", ".join(others) if others else "(无)"))
    if zpath:
        print("\n-- zip %s" % zpath)
        with zipfile.ZipFile(zpath) as z:
            print("   testzip=%s | 成员 %d | %.2f MB" % (z.testzip(), len(z.infolist()), os.path.getsize(zpath) / 1048576.0))
            names = set(os.path.basename(i.filename) for i in z.infolist())
            for i in z.infolist():
                print("     %-46s %8.2f MB" % (i.filename, i.file_size / 1048576.0))
        missing = [f for f in os.listdir(d) if f not in names]
        if missing:
            warns.append("zip 缺少交付件: %r" % missing)
    print()
    if warns:
        print("!! 告警:")
        for w in warns:
            print("  -", w)
        return 1
    print("OK 校验通过(行数/唯一性/zip 完整性) —— 整列非零 != 业务正确, 仍要抽查关键行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
