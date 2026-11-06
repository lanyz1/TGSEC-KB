#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enum_unauth_api.py — 从 JS 抠全量接口 + "全局登录过滤器/白名单"未授权枚举(通用,断点续跑)

为什么要分类:目标站常用**入口级全局登录过滤器**,但白名单比预期宽。
逐条无参 GET,按 body 三分(判据与坑见 references/encrypted-envelope-and-whitelist-enum.md):
  LOGINF  受保护(登录状态已失效 / code:-200 / 登录状态不可用) —— 立刻跳过
  SYSERR  已过鉴权但控制器抛异常(= 在白名单里,配好参数就能打)★最有价值
  OTHER   其余:真数据 或 业务错误,必须读 body 自己判

用法:
  python3 enum_unauth_api.py --base https://api.target.com --js /root/x/umi.js --out en.tsv
  python3 enum_unauth_api.py --base https://api.target.com --paths paths.txt --delay 0.4
断点续跑:再次执行会自动跳过 --out 里已完成的路径。

纪律:只发 GET、无参数、串行、0.3s 间隔;不塞字典、不改 payload —— 这是"遍历"不是"爆破"。
"""
import argparse
import os
import random
import re
import subprocess
import sys
import time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
STATIC = re.compile(r'^/(assets|static|images|image|icon|icons|js|css|fonts|font|favicon)', re.I)
ASSET = re.compile(r'\.(js|css|png|jpe?g|svg|gif|webp|woff2?|ttf|ico|html?|map)$', re.I)
EPRE = re.compile(r'["\'`](/[a-zA-Z][A-Za-z0-9_\-]{1,28}(?:/[A-Za-z0-9_\-.{}$]{1,40}){0,4})["\'`]')
# 敏感词优先排序,先打高价值面
HOT = re.compile(r'(user|order|pay|vip|member|shop|auth|token|account|export|down|money|'
                 r'wallet|balance|admin|bill|withdraw|recharge|config|code|sign|list|info)', re.I)


def harvest(jsfiles):
    eps = set()
    for f in jsfiles:
        s = open(f, errors="replace").read()
        eps |= set(EPRE.findall(s))
    eps = {e for e in eps if not STATIC.match(e) and not ASSET.search(e)}
    return sorted(eps, key=lambda e: (0 if HOT.search(e) else 1, len(e)))


def classify(body):
    if ("登录状态已失效" in body or "登录状态不可用" in body
            or '"code":-200' in body or '"code": -200' in body):
        return "LOGINF"
    if "系统异常" in body:
        return "SYSERR"
    return "OTHER"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="如 https://api.target.com")
    ap.add_argument("--js", nargs="*", default=[], help="前端包(可多个)")
    ap.add_argument("--paths", help="直接给路径清单(每行一个)")
    ap.add_argument("--out", required=True, help="结果 TSV(可续跑)")
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--method", default="GET")
    a = ap.parse_args()

    eps = [l.strip() for l in open(a.paths) if l.strip()] if a.paths else harvest(a.js)
    if not eps:
        sys.exit("没有候选路径:--js 指前端包或 --paths 给清单")

    done = set()
    if os.path.exists(a.out):
        for ln in open(a.out, errors="replace"):
            done.add(ln.split("\t")[0])
    print("候选=%d 已完成=%d" % (len(eps), len(done)), flush=True)

    fh = open(a.out, "a", encoding="utf-8")
    for i, e in enumerate(eps):
        if e in done:
            continue
        try:
            r = subprocess.run(["curl", "-sS", "-k", "--compressed", "--max-time", "12",
                                "-A", UA, "-o", "/tmp/_enum_body.txt",
                                "-w", "%{http_code}|%{size_download}",
                                "-X", a.method, a.base + e],
                               capture_output=True, text=True, timeout=20)
            meta = (r.stdout or "").strip()
            body = open("/tmp/_enum_body.txt", errors="replace").read()
        except Exception as ex:
            meta, body = "ERR", str(ex)[:60]
        cls = classify(body)
        fh.write("%s\t%s\t%s\t%s\n" % (e, meta, cls, re.sub(r"\s+", " ", body[:200])))
        fh.flush()
        if cls != "LOGINF":
            print("[%d/%d] %-6s %s %s | %s"
                  % (i, len(eps), cls, meta, e, re.sub(r"\s+", " ", body[:140])), flush=True)
        time.sleep(a.delay + random.uniform(0, 0.08))
    fh.close()
    print("DONE  → %s" % a.out)


if __name__ == "__main__":
    main()
