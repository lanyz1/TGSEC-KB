#!/usr/bin/env python3
"""Heuristic route-table extractor for OpenAPI-generated JS clients.

Input : one or more .js files, or a directory (scanned recursively for *.js)
Output: TSV  METHOD<TAB>PATH<TAB>file   (deduped, sorted)

Why heuristic: minified bundles interleave `path:` and `method:` inside object
literals with other keys between them, and property order is not guaranteed.
We take a +/-300 char window around each `path:` and look for the nearest
`method:` in that window. Wrong matches are possible; always verify the verb by
probing (a 404 with `Cannot POST /x` means the route is GET/DELETE/PUT only).

Usage:
    python3 extract_client_routes.py ./js > routes.tsv
    python3 extract_client_routes.py api-xxxx.js
"""
import os
import re
import sys

PATH_RE = re.compile(r"""path\s*:\s*["'`]([^"'`]{1,300})["'`]""")
METHOD_RE = re.compile(r"""method\s*:\s*["'`]([A-Za-z]+)["'`]""")
CTRL_RE = re.compile(r"\b([a-zA-Z0-9_]{0,40}Controller[A-Z][a-zA-Z0-9_]*)\b")
WINDOW = 300


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in names:
                    if n.endswith((".js", ".mjs", ".ts")):
                        yield os.path.join(root, n)
        else:
            yield p


def extract(text, src):
    rows = set()
    for m in PATH_RE.finditer(text):
        route = m.group(1)
        lo = max(0, m.start() - WINDOW)
        hi = min(len(text), m.end() + WINDOW)
        window = text[lo:hi]
        mm = METHOD_RE.search(window)
        method = mm.group(1).upper() if mm else "?"
        rows.add((method, route, os.path.basename(src)))
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = set()
    ctrls = set()
    for f in iter_files(sys.argv[1:]):
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError as e:
            print("skip %s: %s" % (f, e), file=sys.stderr)
            continue
        rows |= extract(text, f)
        ctrls |= set(CTRL_RE.findall(text))

    for method, route, src in sorted(rows, key=lambda r: (r[1], r[0])):
        print("%s\t%s\t%s" % (method, route, src))

    if ctrls:
        print("# controllers: %d" % len(ctrls), file=sys.stderr)
        for c in sorted(ctrls):
            print("#  " + c, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
