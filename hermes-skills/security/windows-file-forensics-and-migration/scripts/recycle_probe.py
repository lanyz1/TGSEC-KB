#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""枚举 Windows 回收站: 真实删除时间($I) / 原始完整路径 / 实体大小。

关键: $R 的 mtime 与 PowerShell Shell.Application 的 ModifyDate 都是文件
【原始修改时间】, 不是删除时间。唯一可信的删除时刻在 $I 偏移 16 的 FILETIME。

用法:
  python recycle_probe.py                # 全量列出(按删除时间倒序)
  python recycle_probe.py 凭据 交接       # 只列名字或原路径命中关键字的
"""
import os
import sys
import glob
import struct
import datetime

RB = r"C:\$Recycle.Bin"


def parse_i(path):
    """返回 (删除时间[本地 aware datetime], 原始完整路径)。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) < 28:
        return None
    ft = struct.unpack("<Q", raw[16:24])[0]
    nlen = struct.unpack("<I", raw[24:28])[0]
    name = raw[28:28 + nlen].decode("utf-16-le", "replace").rstrip("\x00")
    # FILETIME 是 UTC。必须显式 tzinfo=utc, 否则 naive datetime 的
    # .astimezone() 不做换算, 会静默返回 UTC 值(时差 8h, 结论全错)。
    dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft / 10)
    dt = dt.replace(tzinfo=datetime.timezone.utc).astimezone()
    return dt, name


def main():
    kws = [a.lower() for a in sys.argv[1:]]
    rows = []
    for sid in glob.glob(os.path.join(RB, "S-*")):
        for ipath in glob.glob(os.path.join(sid, "$I*")):
            try:
                meta = parse_i(ipath)
            except Exception:
                continue
            if not meta:
                continue
            dt, orig = meta
            rpath = os.path.join(sid, "$R" + os.path.basename(ipath)[2:])
            size = os.path.getsize(rpath) if os.path.exists(rpath) else -1
            if kws and not any(k in (orig + ipath).lower() for k in kws):
                continue
            rows.append((dt, orig, size, os.path.exists(rpath)))

    rows.sort(key=lambda r: r[0], reverse=True)
    print("%-20s %12s  %s" % ("真实删除时间", "大小", "原始路径"))
    for dt, orig, size, alive in rows:
        flag = "" if alive else "   [实体缺失]"
        print("%-20s %12d  %s%s" % (dt.strftime("%Y-%m-%d %H:%M:%S"), size, orig, flag))
    print("\n共 %d 条" % len(rows))
    print("还原: python recycle_restore.py <关键字> --go")


if __name__ == "__main__":
    main()
