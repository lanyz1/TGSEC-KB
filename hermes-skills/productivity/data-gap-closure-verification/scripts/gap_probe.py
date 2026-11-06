# -*- coding: utf-8 -*-
"""dump 列缺口核验三件套(配合 SKILL.md 核验流程步骤 1-3)

用法:
  python gap_probe.py headers <dump_dir>
  python gap_probe.py census  <dump_dir> <DB.Table>
  python gap_probe.py overlap <dump_dir> <DB.T1> <col1> <DB.T2> <col2>

约定:dump_dir 下为 <DB>.<Table>.tsv,首行表头,\t 分隔,utf-8-sig。
"""
import sys, os, csv, glob, collections

# 精确 token:禁用宽泛子串(chan/sale 会命中 ChangeMoney 等流水列,把候选集撑爆)
TOK = ('channel_id', 'channelid', 'proxyid', 'parentid', 'parentids', 'sourceparentid',
       'parent2id', 'parent3id', 'invitecode', 'roubarparentid', 'agent_id', 'agentid',
       'teamid', 'team_id', 'group_id', 'groupid', 'spreadid', 'recommender', 'referrer')
KEY = ('roleid', 'accountid', 'userid', 'uid', 'memberid', 'playerid')


def tsv_path(d, t):
    return os.path.join(d, t + '.tsv')


def fieldnames(d, t):
    with open(tsv_path(d, t), encoding='utf-8-sig', errors='replace') as f:
        return f.readline().rstrip('\n').rstrip('\r').split('\t')


def rows(d, t):
    with open(tsv_path(d, t), encoding='utf-8-sig', errors='replace', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            yield r


def headers(d):
    """步骤1:全库表头扫描,列出含候选列的表(区分有/无会员键列)"""
    cand, dicts = [], []
    files = glob.glob(os.path.join(d, '*.tsv'))
    for p in files:
        try:
            with open(p, encoding='utf-8-sig', errors='replace') as f:
                cols = f.readline().rstrip('\n').rstrip('\r').split('\t')
        except Exception:
            continue
        low = [c.strip().lower() for c in cols]
        hit = sorted({c for c in low if any(t == c for t in TOK)})
        if not hit:
            continue
        name = os.path.basename(p)[:-4]
        if any(c in KEY for c in low):
            cand.append((name, hit))
        else:
            dicts.append((name, hit))
    print("扫描 %d 个 TSV" % len(files))
    print("== 候选绑定表(含会员键列, %d) ==" % len(cand))
    for n, h in cand:
        print("  %-58s %s" % (n, ','.join(h[:8])))
    print("== 无会员键列(汇总/字典, %d, 只列前 40) ==" % len(dicts))
    for n, h in dicts[:40]:
        print("  %-58s %s" % (n, ','.join(h[:6])))
    print("\n下一步:对候选表逐个跑 census;覆盖人数可观的源再跑 overlap 验值域")


def census(d, t, sample_cap=5, val_cap=26):
    """步骤2:单表逐列非空普查(排除 '' 和 '0';样例严格限量,防输出冲爆)"""
    cols = fieldnames(d, t)
    cnt, samp, tot = collections.Counter(), {}, 0
    for r in rows(d, t):
        tot += 1
        for k, v in r.items():
            v = (v or '').strip()
            if v in ('', '0'):
                continue
            cnt[k] += 1
            s = samp.setdefault(k, [])
            if len(s) < sample_cap:
                s.append(v[:val_cap])
    print("%s  共 %d 行 / %d 列" % (t, tot, len(cols)))
    for k in cols:
        c = cnt.get(k, 0)
        print("  %-28s %8d  (%5.1f%%)  %s" % (k, c, 100.0 * c / max(1, tot), ','.join(samp.get(k, []))))


def value_set(d, t, col):
    s = set()
    for r in rows(d, t):
        v = (r.get(col) or '').strip()
        if v not in ('', '0'):
            s.add(v)
    return s


def overlap(d, t1, c1, t2, c2):
    """步骤3:值域交叉验证——交集为空即证伪(例:支付通道 ID vs 推广渠道名册 channel_id)"""
    a, b = value_set(d, t1, c1), value_set(d, t2, c2)
    print("%s.%s 不同值 %d" % (t1, c1, len(a)))
    print("%s.%s 不同值 %d" % (t2, c2, len(b)))
    print("交集 %d" % len(a & b))
    print("  A 样例:", sorted(a)[:12])
    print("  B 样例:", sorted(b)[:12])
    print("  交集样例:", sorted(a & b)[:12])
    print("提示:长度/格式截然不同(如 4 位纯数字 vs 6-9 位)= 不同域的 ID,不能当同一字段用")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    mode, d = argv[1], argv[2]
    if mode == 'headers':
        headers(d)
    elif mode == 'census':
        census(d, argv[3])
    elif mode == 'overlap':
        overlap(d, argv[3], argv[4], argv[5], argv[6])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
