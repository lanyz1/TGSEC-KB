#!/usr/bin/env python3
"""发布前脱敏：把自有 IP 段与已知密钥字面量从技能库里刷掉。

用法:
  python3 redact_own_assets.py --root ~/.hermes/skills \
      --ip-regex '154\.219\.127\.\d+' \
      --literals-file /root/audit-<date>/secret_literals.txt \
      --backup /root/audit-<date>/redact-backup

行为:
  - 只改 *.md；命中前先把原文件按相对路径备份到 --backup
  - IP 替换成 <IP-REDACTED>，字面量替换成 <REDACTED>
  - 输出 JSON：files / ip_hits / literal_hits / detail
  - 幂等：已替换过的文件不再命中
退场后必须重建索引并重跑门禁，卡数与分数不应变化。
"""
import argparse, json, os, re, shutil, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.expanduser('~/.hermes/skills'))
    ap.add_argument('--ip-regex', default=r'154\.219\.127\.\d+')
    ap.add_argument('--literals-file', default=None,
                    help='每行一个字面量；# 开头为注释')
    ap.add_argument('--backup', default=None,
                    help='默认 <root 的父目录>/redact-backup')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(a.root))
    backup = a.backup or os.path.join(os.path.dirname(root), 'redact-backup')
    ip_re = re.compile(a.ip_regex)

    literals = []
    if a.literals_file:
        with open(os.path.expanduser(a.literals_file), encoding='utf-8') as f:
            literals = [l.rstrip('\n') for l in f
                        if l.strip() and not l.startswith('#')]

    changed, n_ip, n_lit = [], 0, 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(dirpath, fn)
            try:
                s = open(p, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            new, c1 = ip_re.subn('<IP-REDACTED>', s)
            c2 = 0
            for lit in literals:
                if lit and lit in new:
                    c2 += new.count(lit)
                    new = new.replace(lit, '<REDACTED>')
            if not (c1 or c2):
                continue
            rel = os.path.relpath(p, root)
            if not a.dry_run:
                dst = os.path.join(backup, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(p, dst)
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(new)
            changed.append([rel, c1, c2])
            n_ip += c1
            n_lit += c2

    print(json.dumps({'root': root, 'dry_run': a.dry_run,
                      'files': len(changed), 'ip_hits': n_ip,
                      'literal_hits': n_lit, 'backup': None if a.dry_run else backup,
                      'detail': changed}, ensure_ascii=False, indent=1))
    return 0 if not changed or not a.dry_run else 0


if __name__ == '__main__':
    sys.exit(main())
