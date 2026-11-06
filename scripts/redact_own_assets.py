#!/usr/bin/env python3
"""脱敏自有资产（IP / 主机名 / 密钥字面量）。

口径：目标方 IP/域名是案卷知识要保留；**自有** IP/主机名/出口是归属证据必须抹。

用法：
  python3 scripts/redact_own_assets.py --root ~/.hermes/skills \
      --ip-regex '154\\.219\\.127\\.\\d+' \
      --literals-file /root/audit/secret_literals.txt \
      --backup /root/audit/redact-backup

--literals-file 每行一个字面量（精确匹配）；--dry-run 只统计不落盘。
"""
import argparse, os, re, shutil, sys

TEXT_EXT = {'.md', '.py', '.sh', '.json', '.yaml', '.yml', '.txt', '.html', '.js', '.ts', '.ini', '.conf'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--ip-regex', action='append', default=[])
    ap.add_argument('--literal', action='append', default=[])
    ap.add_argument('--literals-file')
    ap.add_argument('--placeholder', default='<IP-REDACTED>')
    ap.add_argument('--literal-placeholder', default='<REDACTED>')
    ap.add_argument('--backup')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    lits = list(a.literal)
    if a.literals_file:
        with open(a.literals_file, encoding='utf-8') as f:
            lits += [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]
    regs = [re.compile(r) for r in a.ip_regex]
    if not regs and not lits:
        sys.exit('没有给出 --ip-regex 或 --literal')

    files = ip_hits = lit_hits = 0
    for dp, _, fs in os.walk(a.root):
        for fn in fs:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dp, fn)
            try:
                s = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            new, c1, c2 = s, 0, 0
            for r in regs:
                new, n = r.subn(a.placeholder, new)
                c1 += n
            for lit in lits:
                if lit in new:
                    c2 += new.count(lit)
                    new = new.replace(lit, a.literal_placeholder)
            if not (c1 or c2):
                continue
            files += 1
            ip_hits += c1
            lit_hits += c2
            rel = os.path.relpath(p, a.root)
            print('  %-70s ip=%d lit=%d' % (rel, c1, c2))
            if a.dry_run:
                continue
            if a.backup:
                dst = os.path.join(a.backup, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(p, dst)
            open(p, 'w', encoding='utf-8').write(new)

    print('files=%d ip_hits=%d literal_hits=%d%s'
          % (files, ip_hits, lit_hits, ' (dry-run)' if a.dry_run else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
