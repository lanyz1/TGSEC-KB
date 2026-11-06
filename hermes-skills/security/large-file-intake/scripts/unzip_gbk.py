#!/usr/bin/env python3
"""解压中文 Windows 打的 zip（GBK 文件名、无 UTF-8 标志）。

用法: python3 unzip_gbk.py <zip> <outdir>
"""
import os
import shutil
import sys
import zipfile


def fix(name: str) -> str:
    try:
        raw = name.encode("cp437")
    except UnicodeEncodeError:
        return name
    for enc in ("gbk", "gb18030", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return name


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(src)
    n = 0
    for info in z.infolist():
        if info.is_dir():
            continue
        rel = fix(info.filename).replace("\\", "/")
        parts = [p for p in rel.split("/") if p not in ("", ".", "..")]
        if not parts:
            continue
        out = os.path.join(dst, *parts)
        os.makedirs(os.path.dirname(out) or dst, exist_ok=True)
        with z.open(info) as fsrc, open(out, "wb") as fdst:
            shutil.copyfileobj(fsrc, fdst)
        n += 1
    print(f"extracted {n} files -> {dst}")


if __name__ == "__main__":
    main()
