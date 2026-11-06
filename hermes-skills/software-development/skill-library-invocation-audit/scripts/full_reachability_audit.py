#!/usr/bin/env python3
"""全库反向可达测试：用每张卡自己的描述里最稀有的词当现场说法，看检索能否把它调出来。

口径：这张卡的「现场说法」= 描述里 df 最低的 1-3 个专有词（产品名/报错/参数/特征词）。
如果连自己的专有词都调不出 top10，那张卡在实战里基本等于不存在。
"""
import sys, os, json, sqlite3, re, io, contextlib, collections

sys.path.insert(0, "/root/.hermes/arsenal")
import skill_find as SF

DB = "/root/.hermes/arsenal/arsenal.db"
db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
rows = [dict(r) for r in db.execute("SELECT name,description,tags,status,catalog FROM skills")]

df = {}
for t, d in db.execute("SELECT term, df FROM term_df"):
    df[t] = d
df = {k: v for k, v in df.items() if v >= 1}

STOP = set("""use when the and for with from that this are was you your our can will not
skill card trigger scenario 触发 场景 用于 使用 需要 目标 渗透 测试 打法 覆盖 包含 方法 步骤
实战 现场 描述 卡片 技能 时候 怎么 如何 什么 一张 全部 以及 包括""".split())

def toks(s):
    s = re.sub(r"[`*_\[\](){}<>|\\/\"'=:,;.!?~@#$%^&+]+", " ", s or "")
    out = []
    for t in re.split(r"\s+", s):
        t = t.strip().lower()
        if not t or t in STOP or len(t) < 3:
            continue
        if not re.search(r"[a-z0-9\u4e00-\u9fff]", t):
            continue
        out.append(t)
    return out

def qdf(t):
    if t in df:
        return df[t]
    if re.search(r"[\u4e00-\u9fff]", t) and len(t) >= 3:
        bg = [t[i:i+2] for i in range(len(t)-1)]
        vals = [df[b] for b in bg if b in df]
        if len(vals) == len(bg) and vals:
            return min(vals)
    return 10**6  # 索引里没有的词：可能是新模式的好词，优先试

def build_query(r):
    cand = toks(r["description"] or "") + toks(r["tags"] or "")
    if not cand:
        return r["name"].replace("-", " ")
    # 稀有优先，长词优先；去重保序
    scored = sorted(set(cand), key=lambda t: (qdf(t), -len(t)))
    return " ".join(scored[:3])

def find(q, top=10):
    sys.argv = ["skill_find.py", q, "--fast", "--top", str(top), "--json"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            SF.main()
        return json.loads(buf.getvalue())
    except Exception:
        return []

res = []
for i, r in enumerate(rows, 1):
    q = build_query(r)
    hits = find(q)
    names = [h["name"] for h in hits]
    rank = names.index(r["name"]) + 1 if r["name"] in names else 0
    res.append({"name": r["name"], "status": r["status"], "catalog": r["catalog"], "q": q, "rank": rank,
                "top3": names[:3]})
    if i % 200 == 0:
        print(f"[{i}/{len(rows)}] done", file=sys.stderr, flush=True)

top1 = sum(1 for x in res if x["rank"] == 1)
top3 = sum(1 for x in res if 1 <= x["rank"] <= 3)
top10 = sum(1 for x in res if 1 <= x["rank"] <= 10)
miss = [x for x in res if x["rank"] == 0]
for st in ("enabled", "disabled"):
    sub = [x for x in res if x["status"] == st]
    print(json.dumps({
        "status": st, "n": len(sub),
        "top1": sum(1 for x in sub if x["rank"] == 1),
        "top3": sum(1 for x in sub if 1 <= x["rank"] <= 3),
        "top10": sum(1 for x in sub if 1 <= x["rank"] <= 10),
        "miss": sum(1 for x in sub if x["rank"] == 0),
    }, ensure_ascii=False))
print(json.dumps({"n": len(res), "top1": top1, "top3": top3, "top10": top10,
                  "miss": len(miss), "top10_rate": round(top10 / len(res) * 100, 2)}, ensure_ascii=False))
out = os.environ.get("REACH_OUT", "/tmp/full_reachability.json")
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print("MISS_LIST")
for x in miss[:60]:
    print(f"  {x['status']:8s} {x['name']}  <= {x['q']}")
