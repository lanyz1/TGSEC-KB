#!/usr/bin/env python3
"""Webshell / 内存马 静态线索扫描（只读）。

用法:
  python3 webshell_static_scan.py --path /var/www/html --ext php,jsp,aspx
  python3 webshell_static_scan.py --path ./upload --json out.json --show --min-score 30

说明:
  * 输出的是「线索分」(0-100)，不是结论：分数高必须人工看命中行 (--show) 与上下文。
  * 内存马(Agent/Filter)不落文件时本脚本扫不到 —— 走 references/detect-and-kill.md 的内存线。
  * 只读文件，不改动、不外连。
"""
import argparse, json, math, os, re, sys

RULES = [
    # (名称, 正则, 权重)
    ("eval/assert 直调", r"\b(eval|assert)\s*\(", 22),
    ("命令执行族", r"\b(system|shell_exec|passthru|popen|proc_open|exec)\s*\(", 20),
    ("base64+eval 组合", r"base64_decode\s*\([^)]*\)\s*\)?\s*;?", 6),
    ("解压+执行", r"(gzinflate|gzuncompress|str_rot13|strrev)\s*\(", 16),
    ("变量函数调用", r"\$\w{1,3}\s*\(\s*\$_(POST|GET|REQUEST|COOKIE|SERVER)", 26),
    ("动态参数名", r"\$_(POST|GET|REQUEST|COOKIE)\s*\[\s*\$_", 20),
    ("preg_replace /e", r"preg_replace\s*\(.*/e['\"]", 24),
    ("create_function", r"create_function\s*\(", 18),
    ("PHP 配置改写", r"@?\s*ini_set\s*\(\s*['\"]display_errors", 10),
    ("哥斯拉特征", r"getBasicsInfo|substr\s*\(\s*md5\s*\(", 28),
    ("冰蝎/哥斯拉 加密马特征", r"openssl_decrypt|substr\s*\(\s*md5\s*\(\s*\$pass", 22),
    ("蚁剑特征", r"antSword|@ini_set\s*\(\s*['\"]display_errors", 14),
    ("Java 执行族", r"(Runtime\.getRuntime|ProcessBuilder|java\.lang\.Runtime)", 24),
    ("Java 内存马注册", r"(StandardContext|addFilterDef|addServletMapping|ApplicationFilterConfig|addValve|addApplicationEventListener)", 34),
    ("Java Agent", r"(Instrumentation|retransformClasses|VirtualMachine\.attach|defineClass)", 30),
    (".NET 执行族", r"(Request\.Item|HttpContext\.Current|Assembly\.Load|FromBase64String)", 20),
    ("隐藏字符/混淆", r"(\$[a-zA-Z0-9_]{1,2}\s*=\s*['\"][a-zA-Z0-9+/=]{60,}['\"])", 16),
]

PHPFUCK_CHARS = set("()[]!^.,;\t ")


def entropy(s):
    if not s:
        return 0.0
    c = {}
    for ch in s:
        c[ch] = c.get(ch, 0) + 1
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def scan_file(path, ext_ok):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return None
    score, hits = 0, []
    for name, pat, w in RULES:
        m = re.search(pat, text, re.I)
        if m:
            score += w
            line = text[: m.start()].count("\n") + 1
            hits.append({"rule": name, "weight": w, "line": line,
                         "snippet": text.splitlines()[line - 1][:160] if line - 1 < len(text.splitlines()) else ""})
    for i, ln in enumerate(text.splitlines(), 1):
        if len(ln) > 200 and set(ln) <= PHPFUCK_CHARS:
            score += 20
            hits.append({"rule": "字符集混淆(PHPFuck 类)", "weight": 20, "line": i, "snippet": ln[:120]})
    file_ent = entropy(text[:20000])
    if file_ent > 4.6 and len(text) > 500:
        score += 8
        hits.append({"rule": f"熵偏高({file_ent:.2f})", "weight": 8, "line": 0, "snippet": ""})
    return {"path": path, "size": len(text), "entropy": round(file_ent, 2),
            "score": min(score, 100), "hits": hits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--ext", default="php,jsp,jspx,asp,aspx,ashx,jar,class,war")
    ap.add_argument("--min-score", type=int, default=20)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    exts = {e.strip().lower().lstrip(".") for e in a.ext.split(",")}
    targets = [a.path] if os.path.isfile(a.path) else []
    for dp, dn, fn in os.walk(a.path):
        if dp.count(os.sep) - os.path.abspath(a.path).count(os.sep) > 6:
            dn[:] = []
        for f in fn:
            if f.rsplit(".", 1)[-1].lower() in exts:
                targets.append(os.path.join(dp, f))
    results = []
    for p in targets:
        r = scan_file(p, exts)
        if r and r["score"] >= a.min_score:
            results.append(r)
    results.sort(key=lambda r: -r["score"])
    print(f"# 扫描文件 {len(targets)} 个，命中阈值({a.min_score}) {len(results)} 个  (线索分≠结论)")
    for r in results[:40]:
        print(f"[{r['score']:>3}] {r['path']}  entropy={r['entropy']}  {','.join(h['rule'] for h in r['hits'][:4])}")
        if a.show:
            for h in r["hits"]:
                print(f"       L{h['line']} +{h['weight']:>2} {h['rule']}: {h['snippet']}")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"# JSON: {a.json_out}")


if __name__ == "__main__":
    main()
