#!/usr/bin/env python3
"""本地技能库 vs TGSEC 仓库 全量对账

跑法: python3 scripts/library_repo_diff.py [--repo DIR] [--lib DIR] [--out JSON]
输出: 终端摘要 + JSON(四分类 / 整目录字节 / 启用-归档拆分)

两个设计点(都是被坑出来的):
  1. 一次 os.walk 建索引 —— 逐名 os.walk 找路径在 593MB 仓库上 300s 超时被 kill。
  2. 按整目录字节比厚薄 —— 本库把正文拆进 references/, 只看 SKILL.md 会误判「仓库更全」
     (实测 offensive-vuln-classes: SKILL 1.8KB vs 仓 96KB, 整目录 240KB, 内容并没丢)。
"""
import argparse
import hashlib
import json
import os


def build_index(root):
    """name -> {path, size(整目录), sha256(SKILL.md)}; 同名取整目录更大的那个"""
    idx = {}
    for dirpath, _dn, filenames in os.walk(root):
        if 'SKILL.md' not in filenames:
            continue
        md = os.path.join(dirpath, 'SKILL.md')
        try:
            sha = hashlib.sha256(open(md, 'rb').read()).hexdigest()
        except OSError:
            continue
        total = 0
        for dp, _d, fn in os.walk(dirpath):
            for f in fn:
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        name = os.path.basename(dirpath)
        prev = idx.get(name)
        if prev is None or total > prev['size']:
            idx[name] = {'path': dirpath, 'size': total, 'sha': sha}
    return idx


def load_disabled(lib):
    try:
        d = json.load(open(os.path.join(lib, '.disabled.json')))
    except (OSError, ValueError):
        return set()
    return set(d if isinstance(d, list) else d.keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='/root/TGSEC-Qtzuu')
    ap.add_argument('--lib', default=os.path.expanduser('~/.hermes/skills'))
    ap.add_argument('--out', default='/tmp/skill_cmp.json')
    a = ap.parse_args()

    L, R = build_index(a.lib), build_index(a.repo)
    dis = load_disabled(a.lib)
    common = sorted(set(L) & set(R))
    same = [n for n in common if L[n]['sha'] == R[n]['sha']]
    differ = [n for n in common if L[n]['sha'] != R[n]['sha']]
    only_l = sorted(set(L) - set(R))
    only_r = sorted(set(R) - set(L))
    l_thick = [n for n in differ if L[n]['size'] > R[n]['size'] * 1.3 and L[n]['size'] - R[n]['size'] > 20000]
    r_thick = [n for n in differ if R[n]['size'] > L[n]['size'] * 1.3 and R[n]['size'] - L[n]['size'] > 20000]

    print(f"本地 {len(L)} 名 (启用 {len(set(L) - dis)} / 归档 {len(set(L) & dis)})")
    print(f"仓库 {len(R)} 名")
    print(f"交集 {len(common)} · 完全一致 {len(same)} · 有差异 {len(differ)}")
    print(f"仅本地 {len(only_l)} (启用 {len([n for n in only_l if n not in dis])}) · 仅仓库 {len(only_r)}")
    print(f"有差异里: 本地明显更厚 {len(l_thick)} · 仓库明显更厚 {len(r_thick)}")

    def dump(label, names):
        print(f"\n{label}:")
        for n in sorted(names, key=lambda x: max(L[x]['size'], R[x]['size']), reverse=True)[:15]:
            print(f"  {n:38s} 本地 {L[n]['size'] // 1024:7d}K  仓 {R[n]['size'] // 1024:7d}K")

    if r_thick:
        dump('仓库明显更厚 TOP15', r_thick)
    if l_thick:
        dump('本地明显更厚 TOP15', l_thick)

    json.dump({
        'lib_total': len(L), 'repo_total': len(R),
        'common': len(common), 'same': same, 'differ': differ,
        'only_local': only_l, 'only_repo': only_r,
        'local_enabled': sorted(set(L) - dis), 'local_disabled': sorted(set(L) & dis),
        'local_thicker': l_thick, 'repo_thicker': r_thick,
        'sizes': {'local': {n: v['size'] for n, v in L.items()},
                  'repo': {n: v['size'] for n, v in R.items()}},
    }, open(a.out, 'w'), ensure_ascii=False, indent=1)
    print(f"\nJSON: {a.out}")


if __name__ == '__main__':
    main()
