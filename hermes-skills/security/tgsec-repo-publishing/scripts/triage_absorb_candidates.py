#!/usr/bin/env python3
"""Triage cards present in another machine's library but absent locally.

Answers "上面有可吸收的吗" with numbers instead of eyeballing titles:
  1) name diff  2) 5-gram shingle Jaccard against the whole local library
  3) buckets: likely renamed copy vs genuinely new surface

Usage:
  python3 triage_absorb_candidates.py \
      --remote /root/skills.thin-20261022 \
      --local  ~/.hermes/skills \
      [--min-jaccard 0.30] [--top 3] [--json /tmp/triage.json]

Only reads files; never writes to either library.
"""
import argparse
import json
import os
import re
import sys


def card_dirs(root):
    """name -> card directory (a card = dir containing SKILL.md)."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(os.path.expanduser(root)):
        if "SKILL.md" in filenames:
            found.setdefault(os.path.basename(dirpath), dirpath)
            dirnames[:] = []  # do not descend into references/ etc.
    return found


def body(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
    except OSError:
        return ""
    if txt.lstrip().startswith("---"):
        parts = txt.split("---", 2)
        if len(parts) == 3:
            txt = parts[2]
    return txt


def shingles(text, k=5):
    words = re.findall(r"\w+", text.lower())
    if len(words) < k:
        return frozenset()
    return frozenset(hash(" ".join(words[i:i + k])) for i in range(len(words) - k + 1))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", required=True, help="old/thin library root")
    ap.add_argument("--local", required=True, help="current library root")
    ap.add_argument("--min-jaccard", type=float, default=0.30,
                    help="above this the candidate is probably a rename/rewrite (default 0.30)")
    ap.add_argument("--top", type=int, default=3, help="best local matches to report")
    ap.add_argument("--json", help="write machine-readable result here")
    args = ap.parse_args()

    remote = card_dirs(args.remote)
    local = card_dirs(args.local)
    if not remote:
        sys.exit("no SKILL.md under --remote: %s" % args.remote)
    if not local:
        sys.exit("no SKILL.md under --local: %s" % args.local)

    local_sets = {name: shingles(body(os.path.join(path, "SKILL.md")))
                  for name, path in local.items()}

    unique = sorted(set(remote) - set(local))
    print("remote=%d local=%d name-unique=%d" % (len(remote), len(local), len(unique)))

    rows, copies, fresh = [], [], []
    for name in unique:
        cand = shingles(body(os.path.join(remote[name], "SKILL.md")))
        scored = sorted(((jaccard(cand, s), other) for other, s in local_sets.items()),
                        reverse=True)[: args.top]
        best = scored[0][0] if scored else 0.0
        row = {
            "card": name,
            "words": len(re.findall(r"\w+", body(os.path.join(remote[name], "SKILL.md")))),
            "best_jaccard": round(best, 4),
            "best_matches": [{"card": n, "jaccard": round(j, 4)} for j, n in scored],
        }
        rows.append(row)
        (copies if best >= args.min_jaccard else fresh).append(row)

    print("likely rename/rewrite (>= %.2f): %d" % (args.min_jaccard, len(copies)))
    for r in copies:
        print("  %-44s max=%.3f  ~%s" % (r["card"], r["best_jaccard"],
                                         r["best_matches"][0]["card"]))

    print("new-surface candidates: %d" % len(fresh))
    for r in sorted(fresh, key=lambda x: x["card"]):
        print("  %-44s words=%-5d max=%.3f" % (r["card"], r["words"], r["best_jaccard"]))

    print("\nNext: judge by ATTACK SURFACE, not similarity — drop cards whose surface")
    print("the local library already covers at peer level (same product family).")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"remote": len(remote), "local": len(local),
                       "unique": len(unique), "min_jaccard": args.min_jaccard,
                       "likely_copy": copies, "new_surface": fresh}, fh,
                      ensure_ascii=False, indent=1)
        print("json -> %s" % args.json)


if __name__ == "__main__":
    main()
