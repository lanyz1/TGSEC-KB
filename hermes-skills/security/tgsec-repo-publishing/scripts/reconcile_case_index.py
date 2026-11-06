#!/usr/bin/env python3
"""CASE-INDEX 三重对账：课文件 <-> 索引行 <-> 计数。

  python3 reconcile_case_index.py [repo]         # 只体检
  python3 reconcile_case_index.py [repo] --fix   # 补缺失行 + 按实际文件重算计数

非课文件（不计入课数）：README.md、REPORTS-*-INDEX.md、_ 开头。
--fix 时新行插到对应域表最后一行之后（不在底部批次块里乱插空行）。
"""
import os, re, sys, glob


def is_lesson(p):
    b = os.path.basename(p)
    return b.endswith('.md') and b != 'README.md' and not b.startswith('REPORTS-') and not b.startswith('_')


def one_liner(path):
    txt = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'^##\s*一句话\s*\n+\s*(.+)', txt, re.M)
    if not m:
        m = re.search(r'^#\s+(.+)', txt, re.M)
    s = (m.group(1) if m else os.path.basename(path)).strip()
    s = re.sub(r'^[-*\d.\s]+', '', s).replace('|', '\\|')
    return s[:80] or os.path.basename(path)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    fix = '--fix' in sys.argv
    repo = args[0] if args else '/root/TGSEC-Qtzuu'
    idx_path = os.path.join(repo, 'domains/CASE-INDEX.md')
    text = open(idx_path, encoding='utf-8').read()
    lines = text.split('\n')

    files = sorted(f for f in glob.glob(os.path.join(repo, 'domains/*/case-lessons/*.md')) if is_lesson(f))
    rels = [os.path.relpath(f, repo) for f in files]
    indexed = set(re.findall(r'`(domains/[^`]+case-lessons/[^`]+\.md)`', text))
    missing = [r for r in rels if r not in indexed]
    orphan = sorted(p for p in indexed if not os.path.exists(os.path.join(repo, p)))

    counts = {}
    for r in rels:
        counts[r.split('/')[1]] = counts.get(r.split('/')[1], 0) + 1
    head = re.search(r'课（case-lessons）：\*\*(\d+)\*\*', text)

    print('实际课文件: %d · 索引唯一路径: %d · 头部总数: %s' % (len(rels), len(indexed), head.group(1) if head else '缺失'))
    print('文件有索引无: %d' % len(missing))
    for m in missing[:20]:
        print('  +', m)
    print('索引有文件无: %d' % len(orphan))
    for o in orphan[:20]:
        print('  -', o)

    for d, n in sorted(counts.items()):
        m = re.search(r'## `%s`（(\d+)）' % re.escape(d), text)
        got = m.group(1) if m else '无标题'
        print('  %-22s 文件=%-3d 标题=%s%s' % (d, n, got, '' if got == str(n) else '  <== 漂移'))

    if fix and missing:
        for r in missing:
            dom = r.split('/')[1]
            slug = os.path.basename(r)[:-3]
            row = '| `%s` | %s | `%s` | — |' % (slug, one_liner(os.path.join(repo, r)), r)
            start = next((i for i, l in enumerate(lines) if l.startswith('## `%s`' % dom)), None)
            if start is None:
                print('  ! %s 无域标题，跳过 %s' % (dom, slug))
                continue
            i, last = start + 1, None
            while i < len(lines) and not lines[i].startswith('## '):
                if lines[i].startswith('|'):
                    last = i
                i += 1
            if last is None:
                print('  ! %s 无表格，跳过 %s' % (dom, slug))
                continue
            lines.insert(last + 1, row)
        text = '\n'.join(lines)

    if fix:
        total = len(rels)
        for d, n in counts.items():
            text = re.sub(r'(## `%s`（)\d+(）)' % re.escape(d), r'\g<1>%d\g<2>' % n, text)
        text = re.sub(r'(课（case-lessons）：\*\*)\d+(\*\*)', r'\g<1>%d\g<2>' % total, text)
        open(idx_path, 'w', encoding='utf-8').write(text)
        print('已写入：补 %d 行，计数重算为 %d' % (len(missing), total))

    bad = bool(missing or orphan or (head and head.group(1) != str(len(rels))))
    return 1 if (bad and not fix) else 0


if __name__ == '__main__':
    sys.exit(main())
