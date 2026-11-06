#!/usr/bin/env python3
"""把 TTP 关键词补进卡片 frontmatter 的 tags —— 让现场口语能检索到。

原因：skill_find.py 只在 name/description/tags/headings/excerpt 打分，
正文命中仅对已进前 80 名的卡加权 => 关键词只在正文 = 现场调不到。

用法：
  python3 add_meta_triggers.py pairs.json [--lib ~/.hermes/skills] [--dry]

pairs.json:
  [{"card": "network-tunneling", "keywords": ["ncat", "--proxy"]}, ...]

行为：有 tags 列表则追加（去重、大小写不敏感）；无 tags 则在 frontmatter 末尾插一行。
只补长尾词，别塞 渗透/后台/未授权 这类通用词（IDF 会压掉，还抢邻卡位）。
改完必跑 arsenal_build.py + selftest.py + route_eval.py。
"""
import glob, json, os, re, sys

args = sys.argv[1:]
dry = "--dry" in args
lib = os.path.expanduser("~/.hermes/skills")
if "--lib" in args:
    lib = args[args.index("--lib") + 1]
pairs = json.load(open([a for a in args if not a.startswith("--")][0], encoding="utf-8"))

for p in pairs:
    card, toks = p["card"], p["keywords"]
    hits = glob.glob(f"{lib}/*/{card}/SKILL.md") + glob.glob(f"{lib}/{card}/SKILL.md")
    if not hits:
        print(f"NOT FOUND  {card}")
        continue
    path = hits[0]
    s = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", s, re.S)
    if not m:
        print(f"NO FM      {card}")
        continue
    fm = m.group(1)
    if all(t.lower() in fm.lower() for t in toks):
        print(f"ALREADY    {card}")
        continue
    tm = re.search(r"^tags:\s*\[(.*?)\]\s*$", fm, re.M)
    if tm:
        cur = [x.strip() for x in tm.group(1).split(",") if x.strip()]
        add = [t for t in toks if t.lower() not in fm.lower()]
        fm2 = fm[:tm.start()] + "tags: [" + ", ".join(cur + add) + "]" + fm[tm.end():]
    else:
        add = toks
        fm2 = fm.rstrip("\n") + "\ntags: [" + ", ".join(add) + "]"
    if not dry:
        open(path, "w", encoding="utf-8").write(s[:m.start(1)] + fm2 + s[m.end(1):])
    print(f"{'DRY ' if dry else 'ADD '}{','.join(add):<40} {card}")
