#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨盘移动失败后的收尾: 逐文件校验 源 ⊆ 目标, 校验通过才清理源残留。

背景(实测):
  shutil.move 跨盘 = copytree + rmtree。rmtree 删不掉【只读】文件
  (.git/objects/* 是 444), 于是抛 WinError 5 Access is denied 并指向源路径,
  但目标是【已经复制完整】的 —— 源剩下的只是删不掉的残留。
  此时重跑复制毫无意义, 直接删源则可能真丢文件。唯一正确做法是先证明
  源里每个文件都在目标里(同相对路径 + 同字节数), 再清源。

用法:
  python verify_subset_then_clean.py SRC DST            # 只校验, 不动任何文件
  python verify_subset_then_clean.py SRC DST --clean    # 校验通过后清源残留

判据: 缺失 0 ⇒ 复制已完成。建议同时人工确认 目标文件数 >= 源残留文件数。
"""
import os
import sys
import stat
import shutil


def verify(src, dst):
    missing, total = [], 0
    for dp, _dns, fns in os.walk(src):
        rel = os.path.relpath(dp, src)
        for fn in fns:
            sp = os.path.join(dp, fn)
            tp = os.path.join(dst, rel, fn)
            total += 1
            try:
                if not os.path.exists(tp) or os.path.getsize(tp) != os.path.getsize(sp):
                    missing.append(os.path.join(rel, fn))
            except OSError:
                missing.append(os.path.join(rel, fn))
    return total, missing


def clear_readonly_and_rmtree(path):
    for dp, _dns, fns in os.walk(path):
        for fn in fns:
            try:
                os.chmod(os.path.join(dp, fn), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    src, dst = sys.argv[1], sys.argv[2]
    clean = "--clean" in sys.argv

    if not os.path.isdir(src):
        print("源目录不存在: %s" % src)
        return
    if not os.path.isdir(dst):
        print("目标目录不存在, 禁止任何清理: %s" % dst)
        return

    total, missing = verify(src, dst)
    print("%-24s 源文件 %d / 缺失 %d" % (os.path.basename(src.rstrip("\\/")), total, len(missing)), end="  ")

    if missing:
        print("-> 目标不完整, 禁止清理")
        for m in missing[:20]:
            print("     缺失: %s" % m)
        if len(missing) > 20:
            print("     ...另有 %d 项" % (len(missing) - 20))
        return

    print("-> 目标完整 ✔  可安全清理源残留")
    if clean:
        try:
            clear_readonly_and_rmtree(src)
            print("     -> 已清理源残留 ✔")
        except Exception as exc:
            print("     ✘ 清理失败: %s" % exc)
    else:
        print("     -> 加 --clean 执行清理")


if __name__ == "__main__":
    main()
