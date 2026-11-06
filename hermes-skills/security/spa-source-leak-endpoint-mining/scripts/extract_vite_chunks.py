#!/usr/bin/env python3
"""Extract Vite chunk names from __vite__mapDeps arrays or quoted JS paths.

Usage:
  python3 extract_vite_chunks.py index.js assets/ -o chunks.txt
"""
import argparse
import json
import pathlib
import re

MAP_RE = re.compile(
    r"__vite__mapDeps=\(i,m=__vite__mapDeps,d=\(m\.f\|\|\(m\.f=(\[[^\]]*\])\)\)\)"
)
QUOTED_RE = re.compile(
    r"[\"']((?:assets|js|\.)/?[A-Za-z0-9_.\-/]+\.js)[\"']"
)


def names_from(text: str):
    out = []
    match = MAP_RE.search(text)
    if match:
        try:
            out.extend(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    out.extend(QUOTED_RE.findall(text))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="JS files or directories")
    parser.add_argument("-o", "--output", default="chunks.txt")
    args = parser.parse_args()

    seen = []
    for raw in args.paths:
        path = pathlib.Path(raw)
        files = [path] if path.is_file() else list(path.rglob("*.js"))
        for file in files:
            try:
                text = file.read_text(errors="ignore")
            except OSError:
                continue
            for name in names_from(text):
                name = name[2:] if name.startswith("./") else name.lstrip("/")
                if name.endswith(".js") and name not in seen:
                    seen.append(name)

    pathlib.Path(args.output).write_text("\n".join(seen), encoding="utf-8")
    print(f"{len(seen)} chunks -> {args.output}")
    for name in seen[:20]:
        print(name)


if __name__ == "__main__":
    main()
