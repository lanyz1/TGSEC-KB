#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按关键字把回收站里的文件还原回 $I 记录的原始路径。

用法:
  python recycle_restore.py 95306凭据单            # 只看会命中什么, 不写盘
  python recycle_restore.py 95306凭据单 --go       # 真还原
  python recycle_restore.py --all --go             # 全部还原(慎用)

安全设计:
  * 目标已存在同名文件时改存 <name>_restored<ext>, 绝不覆盖现有文件;
  * 还原用 shutil.copy2 而非 move —— $R 留在回收站里当二次保险;
  * 不做任何删除动作。
"""
import os
import sys
import glob
import struct
import shutil

RB = r"C:\$Recycle.Bin"


def parse_i(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) < 28:
        return None
    nlen = struct.unpack("<I", raw[24:28])[0]
    return raw[28:28 + nlen].decode("utf-16-le", "replace").rstrip("\x00")


def main():
    args = sys.argv[1:]
    go = "--go" in args
    every = "--all" in args
    kws = [a for a in args if not a.startswith("--")]
    if not kws and not every:
        print(__doc__)
        return

    hits, done = 0, 0
    for sid in glob.glob(os.path.join(RB, "S-*")):
        for ipath in glob.glob(os.path.join(sid, "$I*")):
            try:
                orig = parse_i(ipath)
            except Exception:
                continue
            if not orig:
                continue
            if not every and not any(k in orig for k in kws):
                continue
            hits += 1
            rpath = os.path.join(sid, "$R" + os.path.basename(ipath)[2:])
            if not os.path.exists(rpath):
                print("跳过(实体缺失): %s" % orig)
                continue
            dst = orig
            if os.path.exists(dst):
                base, ext = os.path.splitext(dst)
                dst = base + "_restored" + ext
            print("%s %s%s" % ("还原" if go else "命中", orig,
                               "" if dst == orig else "  ->  %s" % dst))
            if go:
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(rpath, dst)
                    print("     ✔ %d B" % os.path.getsize(dst))
                    done += 1
                except Exception as exc:
                    print("     ✘ %s" % exc)

    print("\n命中 %d 项, 已还原 %d 项%s" % (hits, done, "" if go else "  (加 --go 才真正写盘)"))


if __name__ == "__main__":
    main()
