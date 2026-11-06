#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""权限覆盖率分析: 找出「没有调用权限检查」的 API handler (Go 项目通用)。

白盒越权审计的「差异法」批量执行工具 —— 手工 grep 回答不了"哪些 handler
漏了检查", 需要函数粒度的 有/无 二元判定。

用法:
    python audit_perm.py <项目根>                       # 默认扫 <根>/backend/api/v1
    python audit_perm.py <项目根> <相对API目录>          # 指定扫描目录
    python audit_perm.py <项目根> --perm-regex '<re>'   # 换权限调用匹配式
    python audit_perm.py <项目根> --method-regex '<re>' # 换 handler 匹配式

输出: 总数 / 覆盖率 / 不含权限检查的 handler 清单。

判读要点(必看):
  * 覆盖率低不一定是漏洞 —— Login/Signup/健康检查本就不需要鉴权。
  * 要找的是「同批同类 handler 里大部分检查了、少数没检查」的例外(差异法)。
  * 权限匹配式要卡在「调用形态」上, 不能卡在关键词上; 默认
    `Check[A-Za-z]*Permission(` 而不是 `[Pp]ermission`。
  * 拿到的候选还要过两条信任边界自检: 变量写入者是不是受害者本人；
    权限是否不对等(平台高权 + 攻击者低权才构成提权)。
"""
import argparse
import glob
import os
import re
import sys

DEFAULT_API_DIR = "backend/api/v1"
DEFAULT_METHOD_RE = r'^func \(s \*(\w+)\) ([A-Z]\w+)\('
DEFAULT_PERM_RE = r'[Cc]heck[A-Za-z]*Permission\('


def extract_funcs(path, method_re):
    """产出 (服务名.方法名, 函数体原文)。用花括号配平截取函数体。"""
    src = open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(method_re, src, re.M):
        svc, name = m.group(1), m.group(2)
        try:
            brace = src.index("{", m.end())
        except ValueError:
            continue
        # 跳过只有声明没函数体的(接口/前置声明)
        if src[brace - 1:brace] == "\n":
            continue
        depth, i = 0, brace
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield f"{svc}.{name}", src[brace:i + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="项目根目录")
    ap.add_argument("api_dir", nargs="?", default=DEFAULT_API_DIR,
                    help=f"API 目录(相对项目根), 默认 {DEFAULT_API_DIR}")
    ap.add_argument("--method-regex", default=DEFAULT_METHOD_RE)
    ap.add_argument("--perm-regex", default=DEFAULT_PERM_RE)
    a = ap.parse_args()

    target = os.path.join(a.root, a.api_dir)
    files = sorted(f for f in glob.glob(os.path.join(target, "*.go"))
                   if not f.endswith("_test.go"))
    if not files:
        sys.exit(f"没找到 .go 文件: {target}")

    perm_re = re.compile(a.perm_regex)
    total = checked = 0
    without = []
    for f in files:
        for full, body in extract_funcs(f, a.method_regex):
            total += 1
            if perm_re.search(body):
                checked += 1
            else:
                without.append((os.path.basename(f), full))

    print(f"扫描目录: {target}")
    print(f"文件数: {len(files)}")
    print(f"handler 总数: {total}")
    if total:
        print(f"含权限检查: {checked}  ({100.0 * checked / total:.1f}%)")
    print(f"不含权限检查: {len(without)}")
    print()
    print("=== 候选(需人工筛: 剔除本就无需鉴权的登录/健康检查等) ===")
    for fn, full in without:
        print(f"  {fn:40s} {full}")


if __name__ == "__main__":
    main()
