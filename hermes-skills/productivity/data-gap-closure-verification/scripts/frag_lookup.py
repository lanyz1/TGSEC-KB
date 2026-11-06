#!/usr/bin/env python
"""片段定位探针 — 客户丢来「987——267」这类带空缺占位的数字片段时,一次跑完四步并给随机基线。

用法(Windows bash,路径给 C:/… 原生形式):
  python frag_lookup.py --xlsx "C:/Users/Administrator/Desktop/表.xlsx" --pkl "$TMPDIR/a.pkl" \\
         --pairs "987,267;973,864;599,567" [--col 手机] [--baseline 200]

  --pkl <缓存>   已存在的 (hdr, rows) pickle 直接复用;给 --xlsx 时会顺手写缓存(别反复重读大表)
  --col  名称    第 2 步在哪个列里做「按序含两端」(默认 手机)
  --baseline N   第 4 步随机对抽样次数(默认 200;0 = 跳过)

四步(见 SKILL.md 第 7 节,缺一不可):
 1 字面形态 \d+[-–—]{1,6}\d+ 逐列汇总      → 证明横杠只是书写占位符,不是表内真值
 2 指定列内「去非数字后按序含两端」        → 硬结论(有/没有)
 3 同一行任意列同时含两端 / 同一格不限顺序  → 覆盖误判(宽表里数字靠巧合共现很常见)
 4 随机三数字片段对的同行共现基线          → 命中 ≤ 基线中位数 = 噪声,不许当结果上报
只打聚合数字 + ≤5 条样例:整列样例会冲爆工具输出。
"""
import argparse, collections, os, pickle, random, re, sys

DASH = re.compile(r'\d+[-\u2013\u2014]{1,6}\d+')


def load(xlsx=None, pkl=None, sheet='Sheet1'):
    if pkl and os.path.exists(pkl):
        with open(pkl, 'rb') as f:
            hdr, rows = pickle.load(f)
        print('[cache] %s: %d 行 x %d 列' % (pkl, len(rows), len(hdr)))
        return hdr, rows
    if not xlsx:
        sys.exit('need --xlsx (首次) 或已存在的 --pkl 缓存')
    import openpyxl
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[sheet] if sheet in wb.sheetnames else wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    hdr = ['' if c is None else str(c) for c in next(it)]
    rows = [list(r) for r in it]
    wb.close()
    print('[load] %s: %d 行 x %d 列' % (xlsx, len(rows), len(hdr)))
    if pkl:
        with open(pkl, 'wb') as f:
            pickle.dump((hdr, rows), f)
        print('[cache] 已写 %s' % pkl)
    return hdr, rows


def digits(s):
    return re.sub(r'\D', '', s)


def bits(items, n=5, width=40):
    for x in items[:n]:
        print('      ', ' | '.join(str(y)[:width] for y in x))
    if len(items) > n:
        print('       …共 %d 条' % len(items))
        


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx')
    ap.add_argument('--pkl')
    ap.add_argument('--sheet', default='Sheet1')
    ap.add_argument('--pairs', required=True, help='a,b;a,b;… 如 987,267;973,864')
    ap.add_argument('--col', default='手机')
    ap.add_argument('--baseline', type=int, default=200)
    a = ap.parse_args()
    hdr, rows = load(a.xlsx, a.pkl, a.sheet)
    pairs = [tuple(p.split(',')) for p in a.pairs.split(';') if p.strip()]
    ci = hdr.index(a.col) if a.col in hdr else None
    rn = hdr.index('行号') if '行号' in hdr else 29   # 本家族:第 30 列 = 行号
    idc = hdr.index('id') if 'id' in hdr else 0
    rowstr = ['\x00'.join(str(v) for v in r if v is not None) for r in rows]

    # 1 字面形态逐列汇总
    per, ex = collections.Counter(), collections.defaultdict(list)
    for r in rows:
        for i, v in enumerate(r):
            if v is None:
                continue
            s = str(v)
            if DASH.search(s):
                per[hdr[i]] += 1
                if len(ex[hdr[i]]) < 3:
                    ex[hdr[i]].append(s[:40])
    print('\n=== 步骤1 字面形态 \\d+[-–—]{1,6}\\d+ 命中(共 %d 格) ===' % sum(per.values()))
    for c, n in per.most_common(8):
        print('   %s: %d   例: %s' % (c, n, ex[c][:2]))
    if not per:
        print('   (无) —— 横杠不在数据里,按步骤2 继续\n')

    # 2 列内按序含两端
    print('=== 步骤2 列「%s」内 去非数字后按序含两端 ===' % a.col)
    if ci is None:
        print('   该列不存在,跳过(先用 --col 指定真实列名)')
    else:
        for x, y in pairs:
            hits = []
            for r in rows:
                v = r[ci]
                if v is None:
                    continue
                d = digits(str(v))
                if x in d and y in d and d.index(x) < d.index(y):
                    hits.append((r[rn], str(v), r[idc]))
            print('   %s -> %s: %d 条' % (x, y, len(hits)))
            bits(hits)

    # 3 同行任意列 / 同格不限顺序
    print('=== 步骤3 同行任意列同时含两端 / 同格不限顺序(只为覆盖误判) ===')
    for x, y in pairs:
        rw = [r for r, s in zip(rows, rowstr) if x in s and y in s]
        ce = [(hdr[i], str(v), r[rn]) for r in rows for i, v in enumerate(r)
              if v is not None and x in digits(str(v)) and y in digits(str(v))]
        print('   %s/%s: 同行共现 %d 行 / 同格共现 %d 格' % (x, y, len(rw), len(ce)))
        bits(ce)

    # 4 随机基线
    if a.baseline > 0:
        base = []
        for _ in range(a.baseline):
            x, y = ('%03d' % random.randint(0, 999) for _ in range(2))
            base.append(sum(1 for s in rowstr if x in s and y in s))
        base.sort()
        print('=== 步骤4 随机基线(%d 次,随机三数字片段对) ===' % a.baseline)
        print('   同行共现行数: 中位 %d / 均值 %.1f / 最大 %d'
              % (base[len(base) // 2], sum(base) / len(base), base[-1]))
        print('   ⇒ 与基线同量级的命中是噪声,不许当结果上报;要报只报明显高于基线的。')


if __name__ == '__main__':
    main()
