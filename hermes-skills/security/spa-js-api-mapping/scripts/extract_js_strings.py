#!/usr/bin/env python3
"""Extract string literals + path/API tokens from (minified) JS for API surface mapping.

Usage: python3 extract_js_strings.py <file-or-dir> ...

Why: grepping minified bundles for keywords often returns 0 hits; extracting ALL
string literals and filtering by shape (starts with '/', contains '/api') is reliable.
Prints path literals and api-ish literals; pipe to grep/awk for further filtering.
"""
import sys, re
from pathlib import Path

STR_RE = re.compile(r"""(['"])((?:\\.|(?!\1).){2,200}?)\1""", re.S)
PATHISH = re.compile(r"^[A-Za-z0-9_\-./{}:$%*\[\]]+$")

def scan(path, out):
    try:
        s = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    for m in STR_RE.finditer(s):
        lit = m.group(2)
        if len(lit) < 2:
            continue
        out.add(lit)

out = set()
for a in sys.argv[1:]:
    p = Path(a)
    if p.is_dir():
        for f in p.rglob("*.js"):
            scan(f, out)
    else:
        scan(p, out)

paths = sorted({x for x in out if x.startswith("/") and PATHISH.match(x)})
apis = sorted({x for x in out if "/api" in x or "/v1" in x or "/v2" in x})
print(f"== path literals ({len(paths)}) ==")
for x in paths:
    print(x)
print(f"\n== api-ish ({len(apis)}) ==")
for x in apis:
    print(x)
