#!/usr/bin/env python3
"""TTP 元数据可调率体检（吸收后必跑）。

原因：skill_find.py 只在 name/description/tags/headings/excerpt 上打分，
body 命中仅对已进前 80 名的卡加权（skill_find.py:168-181）。
=> 打法写进正文但 description/tags 不带关键词 = 现场问不到，等于没吸收。

用法：
  python3 ttp_metadata_check.py pairs.json [arsenal.db]
pairs.json: [{"label": "...", "card": "some-skill", "keywords": ["ncat", "--proxy"]}, ...]
"""
import json, sqlite3, sys

pairs = json.load(open(sys.argv[1], encoding="utf-8"))
db_path = sys.argv[2] if len(sys.argv) > 2 else "/root/.hermes/arsenal/arsenal.db"
db = sqlite3.connect(db_path)
db.row_factory = sqlite3.Row
rows = {r["name"]: dict(r) for r in db.execute("select * from skills")}

ok = miss = 0
missing = []
for p in pairs:
    r = rows.get(p["card"])
    if not r:
        print(f"??  卡不在索引: {p['card']}")
        continue
    meta = ((r["description"] or "") + " " + (r["tags"] or "")).lower()
    if any(k.lower() in meta for k in p["keywords"]):
        ok += 1
        print(f"OK   {p['label']:<24} {p['card']}")
    else:
        miss += 1
        missing.append(p)
        print(f"MISS {p['label']:<24} {p['card']}   缺: {p['keywords'][0]}")
print(f"\n元数据可调 {ok}/{ok+miss} = {round(100*ok/max(1,ok+miss))}%")
if missing:
    print("待补 tags:", json.dumps(missing, ensure_ascii=False))
    sys.exit(1)
