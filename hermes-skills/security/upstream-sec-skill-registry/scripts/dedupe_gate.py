#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dedupe_gate.py - 上游技能包 vs 本库 的内容级去重闸。

判断一个上游 skills 仓库里到底有没有本库真缺口。领域名重合不算数。
只做只读 grep，不改任何文件。

用法:
  python3 dedupe_gate.py --src <上游目录>
  python3 dedupe_gate.py --src <dir> --terms "pixie,karma,module stomping"
  python3 dedupe_gate.py --src <dir> --min-hits 2 --json gap.json
  python3 dedupe_gate.py --lib <本库skills目录> --baseline

判定分桶(避免噪声冒充缺口):
  REF   token 与本库卡名同名 -> 上游在互相引用,不是缺口
  ATTR  出现在"借鉴/参考/综合/来源"行 -> 作者或来源署名
  SOFT  中文标题短语 -> 章节名,人工看一眼
  HOLE  拉丁技术点 0 命中 -> 真缺口,只有它影响退出码
  OK    命中卡数 >= --min-hits

退出码: 0=有 HOLE(值得拉) 1=零 HOLE(别建卡) 2=用法/路径错
"""
import argparse, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

STOP = set("""json http https api url uri html css xml js php sql yaml base shell run list type name mode path file test user host port ioc doc note read write exec code data dump scan cmd arg env var true false null none new old demo info error token key secret bug fix vuln app web server client config debug login admin root local remote target scope case report tool step stage phase level gate rule basic advanced main index usage example output input format warn limit force help version auto manual all any and the for with from not set get post put del head tail curl bash python bash.png""".split())
ATTR_MARK = ("借鉴", "参考", "综合", "来源", "出处", "取自", "吸收")
REF_NAME = re.compile(r"^[a-z0-9][a-z0-9\-_.]{2,}$")

def iter_skill_files(root, pat="SKILL.md"):
    import fnmatch
    for dp, _dn, fn in os.walk(root):
        if ".git" in dp:
            continue
        for f in fn:
            if fnmatch.fnmatch(f, pat) and not f.lower().startswith(("readme", "license", "changelog", "index")):
                yield os.path.join(dp, f)

def guess_lib():
    home = os.path.expanduser("~")
    cands = []
    for pat in ("AppData/Local/hermes/profiles/*/skills/security",
                ".hermes/profiles/*/skills/security",
                "AppData/Local/hermes/skills"):
        cands += glob.glob(os.path.join(home, *pat.split("/")))
    best, n = None, -1
    for c in cands:
        cnt = sum(1 for _ in iter_skill_files(c))
        if cnt > n:
            best, n = c, cnt
    return best, n

def load_lib(root):
    lib = {}
    for p in iter_skill_files(root):
        try:
            lib[os.path.basename(os.path.dirname(p))] = open(p, encoding="utf-8", errors="ignore").read().lower()
        except Exception:
            pass
    return lib

def extract_tokens(text):
    """-> {token: kind}  kind in {code, acronym, heading, attr}"""
    out = {}
    attr_lines = [ln for ln in text.splitlines() if any(m in ln for m in ATTR_MARK)]
    attr_blob = "\n".join(attr_lines).lower()

    def put(t, kind):
        t = (t or "").strip().lower()
        if len(t) < 3 or t in STOP:
            return
        if out.get(t) in ("code",) :
            return
        out[t] = kind

    for m in re.findall(r"`([^`\n]{2,40})`", text):
        t = m.strip().lower()
        if re.fullmatch(r"[a-z0-9_./+ -]{3,40}", t) and not t.replace(".", "").replace("-", "").isdigit():
            put(t, "code")
    for m in re.findall(r"\b([A-Za-z][A-Za-z0-9]{2,13})\b", text):
        if m.isupper() or any(ch.isupper() for ch in m[1:]):
            put(m, "acronym")
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            for seg in re.split(r"[^\u4e00-\u9fffA-Za-z0-9]+", line):
                if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", seg):
                    put(seg, "heading")
    for t in list(out):
        if t in attr_blob and out[t] != "code":
            out[t] = "attr"
        elif re.search(re.escape(t) + r"\s*的", text, re.I):   # "DouglasRao 的 ..." 署名式
            out[t] = "attr"
    return out

def hits_for(t, lib):
    keys = {t}
    if re.search(r"[ /+\-]{1,2}", t):        # "netexec --lsassy" / "feroxbuster / ffuf"
        head = re.split(r"[ /+]+", t.strip())[0]
        if len(head) > 2:
            keys.add(head)
    if re.fullmatch(r"[a-z0-9_.\-+ ]{4,}", t):          # 单复数/连字符变体
        keys.add(t.rstrip("s"))
        keys.add(t.replace("-", " "))
        keys.add(t.replace(" ", ""))
    keys = {k for k in keys if len(k) > 2}
    res = set()
    for c, body in lib.items():
        if any(k in body for k in keys):
            res.add(c)
    return sorted(res)

def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--src")
    ap.add_argument("--glob", default="SKILL.md", help="上游卡的命名模式,如 '*.md'(默认 SKILL.md)")
    ap.add_argument("--lib")
    ap.add_argument("--terms", help="逗号分隔,给则跳过自动抽取")
    ap.add_argument("--min-hits", type=int, default=1)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--quiet-ok", action="store_true", help="只打缺口,不打 OK 行")
    a = ap.parse_args()

    lib_root = a.lib or guess_lib()[0]
    if not lib_root or not os.path.isdir(lib_root):
        print("[X] 找不到本库 skills 目录,用 --lib 指定"); return 2
    lib = load_lib(lib_root)
    print("[基线] 本库 %s -> %d 张 SKILL.md" % (lib_root, len(lib)))
    if a.baseline:
        return 1
    if not a.src or not os.path.isdir(a.src):
        print("[X] --src 必须是含 SKILL.md 的目录"); return 2
    src_cards = list(iter_skill_files(a.src, a.glob))
    print("[上游] %s -> %d 张 SKILL.md" % (a.src, len(src_cards)))
    if not src_cards:
        print("[!] 索引型仓库(无 SKILL.md):只抽 README 仓库表,不建卡"); return 1

    src_names = {os.path.basename(os.path.dirname(x)) for x in src_cards}
    holes, soft, report = [], [], {}
    for p in src_cards:
        name = os.path.basename(os.path.dirname(p)) or os.path.basename(p)[:-3]
        text = open(p, encoding="utf-8", errors="ignore").read()
        toks = ({t.strip().lower(): "code" for t in a.terms.split(",") if t.strip()}
                if a.terms else extract_tokens(text))
        row = {"HOLE": [], "SOFT": [], "REF": [], "ATTR": [], "OK": 0}
        for t, kind in sorted(toks.items()):
            if kind == "attr":
                row["ATTR"].append(t); continue
            if t in lib or t in src_names:      # 本库卡名 或 上游卡互相引用
                row["REF"].append(t); continue
            h = hits_for(t, lib)
            if not h and re.search(r"[ /+\-]{1,2}", t) and len(hits_for(t, lib)) == 0:
                pass
            if len(h) >= a.min_hits:
                row["OK"] += 1
                if not a.quiet_ok:
                    print("   OK   %-30s hits=%-3d %s" % (t[:30], len(h), ",".join(h[:3])))
            elif re.search(r"[\u4e00-\u9fff]", t):
                row["SOFT"].append(t); soft.append((name, t))
            else:
                row["HOLE"].append(t); holes.append((name, t))
                print("   HOLE %-30s hits=0" % t[:30])
        report[name] = row
        print("\n### %-26s OK=%-3d HOLE=%-2d SOFT=%-2d REF=%-2d ATTR=%-2d" %
              (name, row["OK"], len(row["HOLE"]), len(row["SOFT"]), len(row["REF"]), len(row["ATTR"])))

    print("\n" + "=" * 72)
    if holes:
        print("[结论] HOLE(真缺口候选) %d 个 -> 值得拉,逐个看上下文再决定建卡:" % len(holes))
        for n, t in holes:
            print("   - %s :: %s" % (n, t))
        v = 0
    else:
        print("[结论] 零 HOLE -> 本库已覆盖,禁止建重复卡")
        v = 1
    if soft:
        print("\n[SOFT] 中文标题短语 %d 个(多为章节名,人工扫一眼,不影响结论): %s"
              % (len(soft), ", ".join(sorted({t for _, t in soft}))[:400]))
    if a.json_out:
        json.dump({"lib": lib_root, "lib_size": len(lib), "src": a.src, "min_hits": a.min_hits,
                   "holes": holes, "soft": soft, "report": report},
                  open(a.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[存] %s" % a.json_out)
    return v

if __name__ == "__main__":
    sys.exit(main())
