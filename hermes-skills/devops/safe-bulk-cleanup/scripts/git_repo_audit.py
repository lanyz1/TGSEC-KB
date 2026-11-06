#!/usr/bin/env python3
"""Git repo bloat inventory — what is big, what is redundant, what a rewrite would reclaim.

    python3 git_repo_audit.py [repo_path] [--min-mb 1]

Read-only: never writes to the repo. Emits a per-group deletable rollup plus the
measured-vs-estimated note. Pair with a real filter-repo run on a COPY for the
receipt number (see references/git-repo-size-audit-20261002.md).
"""
import argparse
import collections
import os
import re
import subprocess
import sys


def git(repo, *args):
    return subprocess.run(["git", "-c", "core.quotePath=false", *args],
                          capture_output=True, text=True, cwd=repo).stdout


def tracked(repo):
    """HEAD-tracked files with sizes. core.quotePath=false is MANDATORY:
    without it CJK paths come back octal-escaped and every Path() op fails."""
    out = git(repo, "ls-tree", "-r", "-l", "HEAD")
    files = []
    for line in out.splitlines():
        m = re.match(r"^(\d+)\s+blob\s+([0-9a-f]{40})\s+(\d+)\t(.*)$", line)
        if m:
            files.append({"mode": m.group(1), "sha": m.group(2),
                          "size": int(m.group(3)), "path": m.group(4)})
    return files


def history_only(repo, head_shas, floor=500_000):
    """Blobs reachable from history but absent from HEAD: invisible in ls-tree,
    yet still holding the pack open. Only a history rewrite clears them."""
    names = {}
    for line in git(repo, "rev-list", "--objects", "--all").splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and len(parts[0]) == 40:
            names.setdefault(parts[0], parts[1])
    if not names:
        return []
    proc = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objecttype) %(objectname) %(objectsize)"],
        input="\n".join(names), capture_output=True, text=True, cwd=repo)
    out = []
    for line in proc.stdout.splitlines():
        p = line.split()
        if len(p) == 3 and p[0] == "blob" and p[1] not in head_shas and int(p[2]) >= floor:
            out.append({"size": int(p[2]), "sha": p[1], "path": names.get(p[1], "?")})
    return sorted(out, key=lambda x: -x["size"])


def dup_blobs(files, floor=100_000):
    """Same SHA at >1 path = mirror dirs. Bloats the CHECKOUT, costs ~0 in the
    pack (git already stores one copy). Never book these as pack savings."""
    by = collections.defaultdict(list)
    for f in files:
        if f["size"] > floor:
            by[f["sha"]].append(f)
    return {k: v for k, v in by.items() if len(v) > 1}


def mirror_dirs(files):
    """Top-level dirs whose contents substantially duplicate another top-level dir."""
    top = collections.defaultdict(set)
    for f in files:
        head = f["path"].split("/")[0]
        if "/" in f["path"]:
            top[head].add(f["sha"])
    out = []
    tops = list(top)
    for i, a in enumerate(tops):
        for b in tops[i + 1:]:
            if not top[a] or not top[b]:
                continue
            j = len(top[a] & top[b]) / min(len(top[a]), len(top[b]))
            if j > 0.5:
                out.append((a, b, j))
    return out


CATS = [
    ("archive", r"\.(zip|7z|rar|tar\.gz|tgz|gz|xz|bz2)$"),
    ("binary", r"\.(exe|dll|so|dylib|bin|img|apk|ipa|jar|msi|pdb)$"),
    ("media", r"\.(gif|mp4|mov|avi|webm|png|jpg|jpeg|webp|bmp|ico)$"),
    ("pdf", r"\.pdf$"),
    ("data", r"\.(csv|jsonl|json)$"),
    ("wordlist", r"\.(txt|lst|dic)$"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--min-mb", type=float, default=1.0)
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit(f"not a git repo: {repo}")
    floor = int(args.min_mb * 1024 * 1024)

    files = tracked(repo)
    total = sum(f["size"] for f in files)
    pack = re.search(r"size-pack:\s*(\S+ \S+)", git(repo, "count-objects", "-vH"))
    print(f"repo            {repo}")
    print(f"HEAD tracked    {len(files)} files / {total / 1048576:.1f} MB raw")
    print(f"size-pack       {pack.group(1) if pack else '?'}   <- GitHub shows ~this")
    print("\nNOTE: `git rm` + commit shrinks NOTHING (history keeps the blobs).")
    print("      Reclaim requires filter-repo rewrite + gc + FORCE PUSH.")

    print("\n=== single files >%.1f MB ===" % args.min_mb)
    for f in sorted(files, key=lambda x: -x["size"])[:30]:
        if f["size"] >= max(floor, 200_000):
            print(f"  {f['size'] / 1048576:8.2f} MB  {f['path'][:110]}")

    print("\n=== extension rollup (>200KB) ===")
    for name, pat in CATS:
        rx = re.compile(pat, re.I)
        it = [f for f in files if f["size"] > 200_000 and rx.search(f["path"])]
        print(f"  {name:9s} {sum(f['size'] for f in it) / 1048576:8.2f} MB  n={len(it)}")

    dup = dup_blobs(files)
    waste = sum(v[0]["size"] * (len(v) - 1) for v in dup.values())
    print(f"\n=== duplicate-content blobs ===\n  {len(dup)} groups, {waste / 1048576:.1f} MB "
          f"of CHECKOUT waste (pack waste ~= 0)")
    for v in sorted(dup.values(), key=lambda x: -x[0]["size"])[:5]:
        print(f"  {v[0]['size'] / 1048576:7.2f} MB x{len(v)}  {v[0]['path'][:80]}")

    mirrored = mirror_dirs(files)
    if mirrored:
        print("\n=== near-duplicate top-level dirs (mirrors) ===")
        for a, b, j in mirrored[:10]:
            print(f"  {a} <-> {b}  overlap={j:.2f}")

    ho = history_only(repo, {f["sha"] for f in files})
    print(f"\n=== history-only blobs (rewrite-only reclaim) ===\n  "
          f"{len(ho)} blobs / {sum(h['size'] for h in ho) / 1048576:.1f} MB")
    for h in ho[:10]:
        print(f"  {h['size'] / 1048576:7.2f} MB  {h['path'][:95]}")

    print("\nNext: build an explicit literal delete list, cp -a the repo to /tmp,")
    print("and run filter-repo there to get the MEASURED reclaim.")


if __name__ == "__main__":
    main()
