#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GH013 sanitizer: neutralize fake-credential fixtures so GitHub push
protection (secret scanning) stops flagging them. Counterpart note: the local
scan_push guard honors XXXX-style markers; GitHub does NOT — it matches
provider formats + entropy, so replacements must break the FORMAT (short
payloads / EXAMPLE forms), not just add markers.

Usage:
  python3 gh013_sanitize.py [--base <sha>] [--execute] [repo]
    repo  default: cwd
    --base default: HEAD~1 (diff base: files changed in <base>..HEAD only)

Rewrite rules (specific prefixes first):
  (sk|rk)_(live|test)_<10+>       -> {{prefix}}_REDACTED  (short -> below GH min)
  sk-proj-/svcacct-/ant-<10+>     -> {{prefix}}-EXAMPLE
  sk-<24+>                        -> sk-EXAMPLE
  gh[pousr]_<20+>                 -> ghp_EXAMPLE
  github_pat_<20+>                -> github_pat_EXAMPLE
  xox[baprs]-<10+>                -> xoxb-EXAMPLE
  AIza<20+>                       -> AIzaEXAMPLE
  AKIA<16+ [0-9A-Z]> (not EXAMPLE) -> AKIAXXXXEXAMPLEKEY1
New Relic NRAK- fixtures: split in source instead (Rust: concat!("NRAK-", "AA..."))
so test values stay intact while the contiguous format disappears.
"""
import argparse
import re
import subprocess

RULES = [
    (re.compile(r'(sk|rk)_(live|test)_[A-Za-z0-9]{10,}'), lambda m: f'{m.group(1)}_{m.group(2)}_REDACTED'),
    (re.compile(r'sk-proj-[A-Za-z0-9_\-]{10,}'), 'sk-proj-EXAMPLE'),
    (re.compile(r'sk-svcacct-[A-Za-z0-9_\-]{10,}'), 'sk-svcacct-EXAMPLE'),
    (re.compile(r'sk-ant-[A-Za-z0-9_\-]{20,}'), 'sk-ant-EXAMPLE'),
    (re.compile(r'(?<![A-Za-z0-9\-_])sk-[A-Za-z0-9]{24,}'), 'sk-EXAMPLE'),
    (re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'), 'ghp_EXAMPLE'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{20,}'), 'github_pat_EXAMPLE'),
    (re.compile(r'xox[baprs]-[0-9A-Za-z\-]{10,}'), 'xoxb-EXAMPLE'),
    (re.compile(r'AIza[0-9A-Za-z_\-]{20,}'), 'AIzaEXAMPLE'),
]
AKIA = re.compile(r'AKIA[0-9A-Z]{16,}')


def fix_akia(text):
    return AKIA.sub(lambda m: m.group(0) if 'EXAMPLE' in m.group(0) else 'AKIAXXXXEXAMPLEKEY1', text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', nargs='?', default='.')
    ap.add_argument('--base', default=None, help='diff base sha (default: HEAD~1)')
    ap.add_argument('--execute', action='store_true')
    a = ap.parse_args()
    base = a.base or 'HEAD~1'
    files = subprocess.run(
        ['git', '-C', a.repo, 'diff', '--name-only', f'{base}..HEAD'],
        capture_output=True, text=True).stdout.splitlines()
    changed = []
    for rel in files:
        p = f'{a.repo}/{rel}'
        try:
            s = open(p, encoding='utf-8').read()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        o = s
        for rx, rep in RULES:
            s = rx.sub(rep, s)
        s = fix_akia(s)
        if s != o:
            changed.append(rel)
            if a.execute:
                open(p, 'w', encoding='utf-8').write(s)
    for c in changed:
        print(c)
    print(f'{"EXECUTED" if a.execute else "DRY"}: {len(changed)} file(s)')


if __name__ == '__main__':
    main()
