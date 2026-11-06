#!/usr/bin/env python3
"""只读裁卡扫描：重复簇 / 桩卡 / 零使用重资产 / 体积账。不删任何东西。

用法: python3 trim_scan.py [--db arsenal.db] [--out /root/trim_scan.json]
产出: 控制台摘要 + JSON（供二轮人工判定）
"""
import os, re, json, sqlite3, collections, itertools, argparse, datetime

ap = argparse.ArgumentParser()
ap.add_argument('--db', default='/root/.hermes/arsenal/arsenal.db')
ap.add_argument('--out', default='/root/trim_scan.json')
ap.add_argument('--min-jd', type=float, default=0.30, help='描述 Jaccard 候选阈值')
ap.add_argument('--min-score', type=float, default=0.45, help='综合分阈值 0.65*jd+0.35*jb')
a = ap.parse_args()

con = sqlite3.connect(a.db); con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute(
    "select name,description,category,status,path,body_path,use_count from skills")]

CJK = re.compile(r'[\u4e00-\u9fff]')
WORD = re.compile(r'[a-z0-9][a-z0-9\.\-_/]{1,}')
STOP = set('security pentest test testing attack attacks target targets use used when 用于 使用 目标 测试 攻击 渗透 一份 以及 通过 可以 需要 进行 常见 完整 相关'.split())

def toks(s):
    s = (s or '').lower()
    t = set(WORD.findall(s))
    cj = ''.join(CJK.findall(s))
    t |= {cj[i:i+2] for i in range(len(cj) - 1)}
    return {x for x in t if x not in STOP and len(x) > 1}

def dir_stat(p):
    d = os.path.dirname(p); tot = nf = 0
    for r, _, fs in os.walk(d):
        for f in fs:
            try:
                tot += os.path.getsize(os.path.join(r, f)); nf += 1
            except OSError:
                pass
    return tot, nf

cards = []
for r in rows:
    try:
        body = open(r['body_path'], encoding='utf-8', errors='replace').read()
    except OSError:
        body = ''
    sz, nf = dir_stat(r['path'])
    cards.append({**r, 'md_size': len(body.encode()), 'dir_size': sz, 'files': nf,
                  'dtok': toks(r['description']), 'btok': toks(body[:4000])})

# 近似重复：倒排索引 + Jaccard
inv = collections.defaultdict(list)
for i, c in enumerate(cards):
    for t in c['dtok']:
        inv[t].append(i)
cand = collections.Counter()
for t, ids in inv.items():
    if len(ids) > 60:
        continue
    for x, y in itertools.combinations(sorted(ids), 2):
        cand[(x, y)] += 1
pairs = []
for (x, y), n in cand.items():
    if n < 3:
        continue
    A, B = cards[x], cards[y]
    jd = len(A['dtok'] & B['dtok']) / max(1, len(A['dtok'] | B['dtok']))
    jb = len(A['btok'] & B['btok']) / max(1, len(A['btok'] | B['btok']))
    sc = 0.65 * jd + 0.35 * jb
    if sc >= a.min_score and jd >= a.min_jd:
        pairs.append((round(sc, 3), round(jd, 3), round(jb, 3), A, B))
pairs.sort(key=lambda z: -z[0])

parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for _, _, _, A, B in pairs:
    ra, rb = find(A['name']), find(B['name'])
    if ra != rb:
        parent[rb] = ra
clusters = collections.defaultdict(list)
for c in cards:
    clusters[find(c['name'])].append(c)
multi = sorted([v for v in clusters.values() if len(v) > 1], key=len, reverse=True)

stubs = [c for c in cards if c['md_size'] < 900 and len(c['description'] or '') < 90]
thin = [c for c in cards if c['md_size'] < 500]
heavy_zero = sorted([c for c in cards if not (c['use_count'] or 0)], key=lambda c: -c['dir_size'])[:15]

print(json.dumps({
    'total': len(cards),
    'enabled': sum(c['status'] == 'enabled' for c in cards),
    'zero_use': sum(not (c['use_count'] or 0) for c in cards),
    'md_bytes': sum(c['md_size'] for c in cards),
    'dir_bytes': sum(c['dir_size'] for c in cards),
    'dup_pairs': len(pairs), 'dup_clusters': len(multi),
    'cards_in_dup_clusters': sum(len(v) for v in multi),
}, ensure_ascii=False, indent=1))

print('\n=== 重复簇 ===')
for v in multi[:20]:
    print(f"[{len(v)}] " + ' | '.join(f"{c['name']}({c['status'][:3]},{c['use_count'] or 0},{c['md_size']//1024}KB,{c['files']}f)" for c in v))
print('\n=== 高置信对 ===')
for s, jd, jb, A, B in pairs[:30]:
    print(f"{s:.2f} jd={jd:.2f} jb={jb:.2f} {A['name']} <-> {B['name']}")
print(f"\n=== 桩卡(<900B,desc<90): {len(stubs)} | 空壳(<500B): {len(thin)} ===")
for c in stubs[:25]:
    print(f"{c['md_size']:5d}B {c['status'][:3]} use={c['use_count'] or 0} {c['name']}")
print('\n=== 零使用重资产 Top15（只搬不删的候选）===')
for c in heavy_zero:
    print(f"{c['dir_size']/1048576:6.2f}MB {c['files']:4d}f md={c['md_size']//1024:4d}KB {c['status'][:3]} {c['name']}")

json.dump({'clusters': [[{k: c[k] for k in ('name','status','use_count','md_size','dir_size','files','description')} for c in v] for v in multi],
           'pairs': [[s, jd, jb, A['name'], B['name']] for s, jd, jb, A, B in pairs],
           'stubs': [c['name'] for c in stubs], 'thin': [c['name'] for c in thin]},
          open(a.out, 'w'), ensure_ascii=False)
print(f"\nsaved {a.out}")
