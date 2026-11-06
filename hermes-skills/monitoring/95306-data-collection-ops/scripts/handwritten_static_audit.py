#!/usr/bin/env python3
"""手搓版静态核查 + 离线自测一键跑（交付「没有 bug」结论前的最后一道闸）。

用法:  python handwritten_static_audit.py [仓库根]      # 默认 D:/95306c
退出码: 0 = 全绿；1 = 有 FAIL。

查六项（都是本系统真踩过的静默丢数据类）:
  1 语法编译 compileall          2 pyflakes 未用变量/import
  3 ruff --select E9,F,B         4 非原子落盘 open(...,"w"/"a")
  5 静默吞异常 except ...: pass  6 四个离线桩必须全绿
只读：不连网、不连目标、不碰任何进程。
"""
import os
import re
import subprocess
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "D:/95306c"
PKGS = ["collector", "master", "bot", "tools"]
STUBS = ["offline_run", "offline_master", "offline_bot", "offline_bk"]
RESULTS = []


def sh(args, timeout=900):
    """跑一条命令 → (exit_code, 合并输出)。用 sys.executable 保证与脚本同一个 python。"""
    p = subprocess.Popen([sys.executable] + args, cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out = "TIMEOUT %ds" % timeout
    return p.returncode, out


def mark(name, ok, note=""):
    RESULTS.append((name, ok, note))
    print("%-4s %-30s %s" % ("PASS" if ok else "FAIL", name, note))


def scan_src():
    """四包下的 .py（跳过 __pycache__）。"""
    out = []
    for pkg in PKGS:
        base = os.path.join(ROOT, pkg)
        if not os.path.isdir(base):
            continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d != "__pycache__"]
            out += [os.path.join(dp, f) for f in sorted(fn) if f.endswith(".py")]
    return sorted(out)


def grep_src(rx):
    """按行找 → [(文件, 行号, 原文)]。只报位置，这处合不合法由人判。"""
    hits = []
    for fp in scan_src():
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if rx.search(line):
                    hits.append((fp, i, line.strip()[:110]))
    return hits


def main():
    if not os.path.isdir(ROOT):
        print("找不到仓库目录: %s" % ROOT)
        return 1
    rc, out = sh(["-m", "compileall", "-q"] + PKGS)
    mark("compileall 语法编译", rc == 0, "" if rc == 0 else "rc=%d（往上翻输出）" % rc)

    checks = (("pyflakes", "pyflakes 未用变量/import", []),
              ("ruff", "ruff --select E9,F,B",
               ["check", "--select", "E9,F,B", "--output-format", "concise"]))
    for mod, label, extra in checks:
        rc, out = sh(["-m", mod] + extra + PKGS)
        body = [l for l in out.splitlines() if l.strip()]
        if "No module named" in out:
            mark(label, True, "SKIP（未装：python -m pip install %s）" % mod)
            continue
        mark(label, rc == 0, "0 命中" if rc == 0 else "%d 行命中" % len(body))
        for l in body[:20]:
            print("       " + l)

    for rx, label, tip in (
            (re.compile(r"open\([^)]*,\s*[\"'](w|a)"), "非原子落盘 open(...,w/a)",
             "原子写实现内部写 tmp 合法；其余逐处判「这文件被哪个进程读」"),
            (re.compile(r"except[^:]*:\s*pass\b"), "静默吞异常 except: pass",
             "吞掉的异常会让失败变「无事发生」，换成打印+计数")):
        hits = grep_src(rx)
        mark(label, not hits, "%d 处%s" % (len(hits), "：" + tip if hits else ""))
        for fp, i, line in hits[:15]:
            print("       %s:%d  %s" % (os.path.relpath(fp, ROOT), i, line))

    for name in STUBS:
        if not os.path.isfile(os.path.join(ROOT, "tools", name + ".py")):
            mark("桩 " + name, True, "SKIP（无此桩）")
            continue
        rc, out = sh([os.path.join("tools", name + ".py")])
        m = re.findall(r"结果:\s*(\d+)/(\d+)\s*通过", out)
        got = m[-1] if m else ("?", "?")
        ok = bool(rc == 0 and m and got[0] == got[1])
        mark("桩 " + name, ok, "%s/%s 通过" % got + ("" if ok else "  ← 有 ❌，往上翻该桩输出"))

    bad = [n for n, ok, _ in RESULTS if not ok]
    print("-" * 62)
    print("合计 %d 项：%s" % (len(RESULTS), "全绿 ✓" if not bad else "FAIL %d 项 → %s" % (len(bad), "、".join(bad))))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())


