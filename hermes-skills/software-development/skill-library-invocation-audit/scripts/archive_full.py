#!/usr/bin/env python3
"""把 card_diff.json 里「包内更全」的卡归档成 <skill>/references/full.md，并在主卡插指引行。

用法:
    python3 archive_full.py <card_diff.json> [--skip name1,name2] [--local /root/.hermes/skills]

幂等:
    - 已有 references/full.md → 跳过
    - SKILL.md 已含 'references/full.md' → 只补文件不重复插行
    - 已手工拆分的卡（partN）用 --skip 排除

实测(2026-10-22):93 张 → 75 归档 / 18 已有 / 1 手工跳过 / 0 失败，5.37MB。
"""
import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    rows = json.load(open(sys.argv[1]))
    local_root = Path('/root/.hermes/skills')
    skip = set()
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--skip' and i + 1 < len(args):
            skip |= {x.strip() for x in args[i + 1].split(',') if x.strip()}
            i += 2
        elif args[i] == '--local' and i + 1 < len(args):
            local_root = Path(args[i + 1])
            i += 2
        else:
            i += 1

    local = {}
    for p in local_root.rglob('SKILL.md'):
        local.setdefault(p.parent.name, p)

    done, skipped, failed = [], [], []
    for r in rows:
        name = r['name']
        if name in skip or name not in local:
            skipped.append((name, 'skip-list' if name in skip else 'no-local'))
            continue
        lp = local[name]
        ref = lp.parent / 'references' / 'full.md'
        if ref.exists():
            skipped.append((name, 'already'))
            continue
        try:
            ref.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(r['path'], ref)
            text = lp.read_text(errors='ignore')
            if 'references/full.md' not in text:
                lines = text.splitlines(keepends=True)
                idx, cnt = None, 0
                for n, ln in enumerate(lines):
                    if ln.strip() == '---':
                        cnt += 1
                        if cnt == 2:
                            idx = n
                            break
                note = (f"\n> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）："
                        f"`skill_view(name='{name}', file_path='references/full.md')`\n")
                lines.insert(idx + 1 if idx is not None else 0, note)
                lp.write_text(''.join(lines))
            done.append(name)
        except Exception as e:  # noqa: BLE001
            failed.append((name, str(e)[:80]))

    print(json.dumps({'done': len(done), 'skipped': len(skipped), 'failed': len(failed)}, ensure_ascii=False))
    print('skipped:', skipped[:10])
    print('failed:', failed[:10])
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
