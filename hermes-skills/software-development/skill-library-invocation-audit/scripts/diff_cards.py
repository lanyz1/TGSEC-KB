#!/usr/bin/env python3
"""技能包吸收：md5 内容级比对包内 SKILL.md 与本地库，四分类 + 包内更全清单。

用法:
    python3 diff_cards.py <包内根目录> [本地库根]
    python3 diff_cards.py /root/absorb_pkg/unpacked /root/.hermes/skills

输出:
    stdout 摘要 + top10;写 <包根>/card_diff.json（包内更全的卡，按唯一行数降序）

为什么不用体积:
    体积法只抓「包内更大」，会漏掉「本地重构后变小、正文丢了」的卡。
    实测(2026-10-22):体积法报 1 张有增量;md5 实测 93 张(21 张 >60KB 全文)。
"""
import hashlib
import json
import sys
from pathlib import Path


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    pkg_root = Path(sys.argv[1])
    local_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / '.hermes' / 'skills'

    local = {}
    for p in local_root.rglob('SKILL.md'):
        local.setdefault(p.parent.name, p)

    pkg = {}
    for p in pkg_root.rglob('SKILL.md'):
        pkg.setdefault(p.parent.name, []).append(p)

    same = pkg_bigger = local_bigger = only_pkg = 0
    rows = []
    for name, paths in pkg.items():
        if name not in local:
            only_pkg += 1
            continue
        lp = local[name]
        if any(md5(pp) == md5(lp) for pp in paths):
            same += 1
            continue
        pp = max(paths, key=lambda x: x.stat().st_size)
        sa, sb = pp.stat().st_size, lp.stat().st_size
        if sa <= sb:
            local_bigger += 1
            continue
        try:
            pa = {x.strip() for x in pp.read_text(errors='ignore').splitlines() if len(x.strip()) > 12}
            pb = {x.strip() for x in lp.read_text(errors='ignore').splitlines() if len(x.strip()) > 12}
            uniq = len(pa - pb)
        except Exception:
            uniq = -1
        pkg_bigger += 1
        rows.append({'name': name, 'pkg': sa, 'local': sb, 'unique_lines': uniq, 'path': str(pp)})

    rows.sort(key=lambda r: -r['unique_lines'])
    out = pkg_root / 'card_diff.json'
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))

    print(json.dumps({
        'pkg_names': len(pkg),
        'local_cards': len(local),
        'identical_md5': same,
        'pkg_bigger': pkg_bigger,
        'local_bigger': local_bigger,
        'only_in_pkg': only_pkg,
        'out': str(out),
    }, ensure_ascii=False, indent=1))
    print('\ntop10 包内更全（按唯一行数）:')
    for r in rows[:10]:
        print(f"  {r['name']}: pkg={r['pkg']} local={r['local']} uniq_lines={r['unique_lines']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
