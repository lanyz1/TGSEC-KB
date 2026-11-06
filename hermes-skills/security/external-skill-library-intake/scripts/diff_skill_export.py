#!/usr/bin/env python3
"""Diff an external agent skill-library export against a local Hermes library.

Usage:
    python3 diff_skill_export.py <zip|tar|dir> [--local DIR] [--json OUT]

Buckets every skill by normalized directory name:
    miss          not present locally
    same          present, size within +/-10%
    upstream_fat  present, upstream SKILL.md >1.1x larger (upgrade candidate)
    local_fat     present, local file >1.1x larger (keep local)

Tiers each `miss` entry: cjk_fat / en_fat / small / stub.
Zips produced on Chinese Windows (GBK names, no UTF-8 flag) are repaired.
"""
import argparse
import json
import os
import shutil
import tarfile
import tempfile
import zipfile


def norm(name):
    return name.lower().replace("-", "").replace("_", "").strip()


def fix_zip_name(name):
    try:
        raw = name.encode("cp437")
    except UnicodeEncodeError:
        return name
    for enc in ("gbk", "gb18030", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return name


def safe_parts(rel):
    return [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".", "..")]


def extract_zip(path, dst):
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = safe_parts(fix_zip_name(info.filename))
            if not parts:
                continue
            out = os.path.join(dst, *parts)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with z.open(info) as src, open(out, "wb") as fh:
                shutil.copyfileobj(src, fh)


def extract_tar(path, dst):
    with tarfile.open(path) as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            parts = safe_parts(m.name)
            if not parts:
                continue
            out = os.path.join(dst, *parts)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            f = tf.extractfile(m)
            if f is None:
                continue
            with f, open(out, "wb") as fh:
                shutil.copyfileobj(f, fh)


def walk_skills(root):
    out = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        if "SKILL.md" not in filenames:
            continue
        p = os.path.join(dirpath, "SKILL.md")
        name = os.path.basename(dirpath)
        out.setdefault(norm(name), []).append((name, p, os.path.getsize(p)))
    return out


def tier(path, size):
    if size < 1500:
        return "stub"
    try:
        head = open(path, encoding="utf-8", errors="replace").read(4000)
    except OSError:
        head = ""
    cjk = sum(1 for ch in head if "\u4e00" <= ch <= "\u9fff")
    ratio = cjk / max(1, len(head))
    if size > 3000 and ratio > 0.03:
        return "cjk_fat"
    if size > 6000:
        return "en_fat"
    return "small"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("--local", default=os.path.expanduser("~/.hermes/skills"))
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    tmp = None
    if os.path.isfile(args.pack):
        tmp = tempfile.mkdtemp(prefix="skilldiff_")
        if zipfile.is_zipfile(args.pack):
            extract_zip(args.pack, tmp)
        else:
            extract_tar(args.pack, tmp)
        packroot = tmp
    else:
        packroot = args.pack

    upstream = walk_skills(packroot)
    local = walk_skills(os.path.expanduser(args.local))

    res = {"pack": args.pack, "pack_skills": len(upstream),
           "local_skills": len(local), "miss": [], "same": [],
           "upstream_fat": [], "local_fat": []}

    for key, entries in upstream.items():
        name, path, size = entries[0]
        if key not in local:
            res["miss"].append({"name": name, "size": size,
                                "tier": tier(path, size), "path": path})
            continue
        lsize = local[key][0][2]
        if size > lsize * 1.1:
            res["upstream_fat"].append({"name": name, "upstream": size, "local": lsize})
        elif lsize > size * 1.1:
            res["local_fat"].append({"name": name, "upstream": size, "local": lsize})
        else:
            res["same"].append({"name": name})

    res["miss"].sort(key=lambda x: -x["size"])
    res["upstream_fat"].sort(key=lambda x: -(x["upstream"] - x["local"]))

    print("pack=%d local=%d" % (res["pack_skills"], res["local_skills"]))
    for bucket in ("miss", "same", "upstream_fat", "local_fat"):
        print("%s: %d" % (bucket, len(res[bucket])))
    tiers = {}
    for m in res["miss"]:
        tiers[m["tier"]] = tiers.get(m["tier"], 0) + 1
    print("miss tiers:", tiers)
    print("-- miss top 25 (size, tier, name)")
    for m in res["miss"][:25]:
        print("  %9d %-8s %s" % (m["size"], m["tier"], m["name"]))
    print("-- upstream_fat top 15 (upstream vs local)")
    for m in res["upstream_fat"][:15]:
        print("  %9d vs %8d  %s" % (m["upstream"], m["local"], m["name"]))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
        print("json ->", args.json_out)

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
