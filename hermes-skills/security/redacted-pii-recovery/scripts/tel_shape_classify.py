#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脱敏手机号字段:形态分类 / 虚拟号池判定 / 双校验交叉还原

用法:
  python tel_shape_classify.py shape   <csv> <tel_col> [name_col] [addr_col]
  python tel_shape_classify.py pool    <csv> <tel_col>
  python tel_shape_classify.py restore <csv> <tel_col> <addr_col> <name_col> [out.csv]

约定电话字段值形如:
  <PHONE-REDACTED>            完整明文
  136*****720            掩码(前3后3)
  136****7200            掩码(前3后4)
  <PHONE-REDACTED>-261        虚拟转接号(分机以 '-' 或 '转' 连接)
  ********               全星号
"""
import csv, re, sys, collections

csv.field_size_limit(10 ** 9)

RE_PLAIN  = re.compile(r'^1[3-9]\d{9}$')
RE_MASK3  = re.compile(r'^1\d{2}\*+(\d{3})$')        # 前3后3
RE_MASK4  = re.compile(r'^1\d{2}\*+(\d{4})$')        # 前3后4
RE_VIRT   = re.compile(r'^(\d{11})[-转](\d{1,6})$')  # 虚拟转接号 -> 主号/分机
RE_STAR   = re.compile(r'^\**$')
RE_INADDR = re.compile(r'1[3-9]\d{9}')               # 地址栏里内嵌的真号


def norm(s):
    """地址归一化: 去空白/中英文标点, 否则同址不同串会导致关联全失败"""
    return re.sub(r'[\s,，。;；、|/]+', '', s or '')


def classify(tel):
    t = (tel or '').strip()
    if RE_PLAIN.match(t):
        return 'plain'
    if RE_VIRT.match(t):
        return 'virt'
    if RE_MASK3.match(t):
        return 'mask3'
    if RE_MASK4.match(t):
        return 'mask4'
    if not t or RE_STAR.match(t):
        return 'empty_or_star'
    return 'other'


def _rows(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        for row in rd:
            yield row


# ---------- shape: 形态分布 ----------
def cmd_shape(path, tel_col, name_col=None, addr_col=None):
    c, samples, n = collections.Counter(), collections.defaultdict(list), 0
    for row in _rows(path):
        n += 1
        k = classify(row.get(tel_col))
        c[k] += 1
        if len(samples[k]) < 3:
            samples[k].append((
                row.get(name_col) if name_col else None,
                (row.get(tel_col) or '').strip(),
                (row.get(addr_col) or '')[:60] if addr_col else None,
            ))
        if n % 500000 == 0:
            print("  ... %d %s" % (n, dict(c)), file=sys.stderr)
    print("总行: %d" % n)
    for k, v in c.most_common():
        print("  %-14s %9d  %5.2f%%" % (k, v, 100.0 * v / max(n, 1)))
    print("\n样本:")
    for k, ss in samples.items():
        for s in ss:
            print("  [%s] %s" % (k, s))
    print("\n★ 若上游口径称某字段为'明文手机号', 以上表为准 —— 上游常把虚拟主号算作明文")


# ---------- pool: 虚拟号池判定 ----------
def cmd_pool(path, tel_col):
    mains, total = collections.Counter(), 0
    for row in _rows(path):
        m = RE_VIRT.match((row.get(tel_col) or '').strip())
        if m:
            total += 1
            mains[m.group(1)] += 1
    if not mains:
        print("无虚拟转接号")
        return
    print("虚拟转接号总数: %d" % total)
    print("唯一主号数:     %d" % len(mains))
    print("平均复用(分机/主号): %.1f" % (total / len(mains)))
    print("\n主号 top15:")
    for k, v in mains.most_common(15):
        print("  %s  %d" % (k, v))
    seg = collections.Counter()
    for k, v in mains.items():
        seg[k[:3]] += v
    print("\n主号号段分布(前3位) —— 全同段 = 单一运营商号池:")
    for k, v in seg.most_common():
        print("  %s: %d" % (k, v))
    print("\n★ 判定: 复用率 >> 1 ⇒ 隐私号池, 分机号是随机路由 key, 不可逆, 只能查绑定表")


# ---------- restore: 双校验交叉还原 ----------
def cmd_restore(path, tel_col, addr_col, name_col, out=None):
    pool, rows, cand_rows, hit = {}, 0, 0, 0
    for row in _rows(path):
        rows += 1
        addr = row.get(addr_col) or ''
        if not addr or '*' in addr:          # 地址本身被脱敏的直接跳过
            continue
        cands = RE_INADDR.findall(addr)
        if not cands:
            continue
        cand_rows += 1
        t = (row.get(tel_col) or '').strip()
        mm = RE_MASK3.match(t) or RE_MASK4.match(t)
        if not mm:
            continue
        p3 = t[1:3]                          # t[0] 恒为 '1'
        l3 = mm.group(1)[-3:]
        ok = [c for c in cands if c[1:3] == p3 and c[-3:] == l3]
        if ok:                               # ★ 两端都验, 单端会误配
            hit += 1
            pool[(row.get(name_col) or '', norm(addr))] = ok[0]
    print("总行: %d | 地址含11位号: %d | 双校验命中: %d | 确认key: %d | 唯一真号: %d"
          % (rows, cand_rows, hit, len(pool), len(set(pool.values()))))

    if out:
        written = 0
        with open(out, 'w', encoding='utf-8-sig', newline='') as o:
            w = csv.writer(o)
            w.writerow(['姓名', '原电话', '形态', '确认真号', '地址'])
            for row in _rows(path):
                k = (row.get(name_col) or '', norm(row.get(addr_col) or ''))
                if k in pool:
                    w.writerow([k[0], (row.get(tel_col) or '').strip(),
                                classify(row.get(tel_col)), pool[k],
                                (row.get(addr_col) or '')[:80]])
                    written += 1
        print("输出: %s (%d 行)" % (out, written))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'shape':
        cmd_shape(a[1], a[2], a[3] if len(a) > 3 else None, a[4] if len(a) > 4 else None)
    elif a and a[0] == 'pool':
        cmd_pool(a[1], a[2])
    elif a and a[0] == 'restore':
        cmd_restore(a[1], a[2], a[3], a[4], a[5] if len(a) > 5 else None)
    else:
        print(__doc__)
