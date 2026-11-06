#!/usr/bin/env python3
"""Mine candidate backend endpoints from JS chunks.

Usage:
  python3 mine_endpoints.py assets/ -o endpoints.txt
"""
import argparse
import pathlib
import re

PATTERNS = [
    re.compile(r"[\"'`](/?[A-Za-z0-9_./-]+\.php(?:\?[^\"'`]*)?)[\"'`]"),
    re.compile(
        r"[\"'`](/(?:api|v\d+|webv\d+|admin|user|pay|withdraw|upload)"
        r"/[A-Za-z0-9_./?=&%-]{2,140})[\"'`]"
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="JS files or directories")
    parser.add_argument("-o", "--output", default="endpoints.txt")
    args = parser.parse_args()

    hits = set()
    for raw in args.paths:
        path = pathlib.Path(raw)
        files = [path] if path.is_file() else list(path.rglob("*.js"))
        for file in files:
            try:
                text = file.read_text(errors="ignore")
            except OSError:
                continue
            for pattern in PATTERNS:
                hits.update(pattern.findall(text))

    ordered = sorted(hits)
    pathlib.Path(args.output).write_text("\n".join(ordered), encoding="utf-8")
    print(f"{len(ordered)} endpoints -> {args.output}")
    for endpoint in ordered[:40]:
        print(endpoint)


if __name__ == "__main__":
    main()
