#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""权限覆盖率分析: 列出「函数体内没调权限校验」的 API handler。

差异法第 3 步(找例外)的自动化。第 2 步(建对照组)与第 4 步(排合理例外)必须人工做, 否则全是误报。
为什么需要对照组: "没检查"极可能是设计如此(公开接口), 也可能校验在别处
(中间件/store 层/拦截器)。只有"项目确实有权限模型 + 这个 handler 是例外"才是漏洞。

用法:
    python audit_perm.py <源码根> [--recv REGEX] [--check REGEX] [--glob GLOB]
例:
    python audit_perm.py D:/0day/bytebase
    python audit_perm.py D:/0day/yearning --glob '**/*.go'
"""
import argparse
import glob
import os
import re
import sys

# 默认适配 Go: func (s *XxxService) Method(  —— connect-go / gin 项目常见
DEF_RECV = r'^func \(s \*(\w+)\) ([A-Z]\w+)\('
DEF_CHECK = r'[Cc]heck[A-Za-z]*[Pp]ermission\('
DEF_GLOB = "**/api/**/*.go"


def extract_handlers(path, recv_re):
    """抽出 (完整名, 函数体)。花括号配对, 不依赖缩进/格式。"""
    src = open(path, encoding="utf-8", errors="replace").read()
    for m in recv_re.finditer(src):
        svc, name = m.group(1), m.group(2)
        brace = src.find("{", m.end())
        if brace < 0:
            continue
        depth, i = 0, brace
        while i < len(src):
            ch = src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield "%s.%s" % (svc, name), src[brace:i + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--recv", default=DEF_RECV, help="方法定义正则, 需 2 个捕获组(类型/方法名)")
    ap.add_argument("--check", default=DEF_CHECK, help="校验调用正则")
    ap.add_argument("--glob", default=DEF_GLOB, help="相对 root 的匹配(默认 **/api/**/*.go)")
    ap.add_argument("--max-list", type=int, default=200)
    a = ap.parse_args()

    recv_re = re.compile(a.recv, re.M)
    check_re = re.compile(a.check)
    files = sorted(f for f in glob.glob(os.path.join(a.root, a.glob), recursive=True)
                   if not f.endswith("_test.go"))
    if not files:
        sys.exit("没有匹配文件: %s (用 --glob 调整)" % os.path.join(a.root, a.glob))

    total = checked = 0
    without = []
    for f in files:
        for full, body in extract_handlers(f, recv_re):
            total += 1
            if check_re.search(body):
                checked += 1
            else:
                without.append((os.path.basename(f), full))

    print("扫描文件: %d   handler 总数: %d" % (len(files), total))
    if total:
        print("函数体内含校验调用: %d (%.1f%%)" % (checked, 100.0 * checked / total))
    print("不含校验调用: %d   <- 候选, 必须逐个人工筛" % len(without))
    print("\n=== 待人工判断(合理例外: Login/Signup/Refresh/Logout/健康检查) ===")
    for fn, full in without[:a.max_list]:
        print("  %-36s %s" % (fn, full))
    if len(without) > a.max_list:
        print("  ... 还有 %d 条" % (len(without) - a.max_list))
    print("\n提醒: 校验也可能在中间件/store 层/拦截器, 或该 handler 调了封装函数 ——")
    print("      判定前先在该函数体内找间接调用, 并确认它是不是公开接口。")
    print("      『没检查』不等于漏洞: 先有对照组证明项目确实有权限模型。")


if __name__ == "__main__":
    main()
