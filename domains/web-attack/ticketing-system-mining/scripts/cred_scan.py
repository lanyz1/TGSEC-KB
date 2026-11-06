#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Credential-shaped regex scanner over a mined corpus (ticket dumps, chat logs, docs).

Usage:
    python3 cred_scan.py <dir-or-file> [out.txt]

Walks *.json/*.txt/*.md/*.html/*.csv/*.log, applies credential-shaped patterns
(EN + RU keywords, email/password adjacency, API-key/token shapes), dedupes
fragments, writes hits to out.txt (default: cred_scan_hits.txt).
Tune/extend PATTERNS per target. Review hits manually.
"""
import re
import sys
import pathlib

PATTERNS = [
    # email + adjacent password-ish value
    re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s*(?:/|\||:|,)\s*[A-Za-z0-9!@#$%^&*._-]{6,}'),
    # password / login keywords (EN + RU)
    re.compile(r'password\S*[:=]?\s*\S{4,30}', re.I),
    re.compile(r'passwd\S*[:=]?\s*\S{4,30}', re.I),
    re.compile(r'пароль\S*[:=]?\s*\S{4,30}', re.I),
    re.compile(r'логин\S*[:=]?\s*\S{4,30}', re.I),
    re.compile(r'creds?\S*[:=]?\s*\S{4,60}', re.I),
    re.compile(r'креды\S*[:=]?\s*\S{4,60}', re.I),
    # API keys / secrets / tokens
    re.compile(r'api[_ -]?key[^\n"]{0,70}', re.I),
    re.compile(r'client[_ -]?secret[^\n"]{0,70}', re.I),
    re.compile(r'secret[_ -]?key[^\n"]{0,70}', re.I),
    re.compile(r'access[_ -]?token[^\n"]{0,70}', re.I),
    # token shapes
    re.compile(r'st\.[A-Za-z0-9-]{10,}\.[A-Za-z0-9_-]{10,}'),   # Infisical service token
    re.compile(r'hskey-[A-Za-z0-9_-]{8,}'),                      # headscale
    re.compile(r'tskey-[A-Za-z0-9]{8,}'),                        # tailscale
    re.compile(r'sk-[A-Za-z0-9]{20,}'),                          # OpenAI-style
    re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,}'),                 # Slack
]

EXTS = ('.json', '.txt', '.md', '.html', '.csv', '.log', '.jsonl')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    root = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else 'cred_scan_hits.txt')

    files = [root] if root.is_file() else [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in EXTS]
    seen, hits = set(), []
    for p in files:
        try:
            t = p.read_text(errors='ignore')
        except Exception:
            continue
        for pat in PATTERNS:
            for m in pat.finditer(t):
                frag = t[max(0, m.start() - 60):m.end() + 60].replace('\n', ' ')
                key = frag[40:140]
                if key in seen:
                    continue
                seen.add(key)
                hits.append(f"{p.name} | {frag[:260]}")
    out_path.write_text('\n'.join(hits), encoding='utf-8')
    print(f"scanned {len(files)} files, {len(hits)} hits -> {out_path}")


if __name__ == '__main__':
    main()
