#!/usr/bin/env python3
"""Two-phase cleanup: archive small valuable files from doomed dirs, then delete them.

Proven pattern (ran 2026-09-11 on the operator box: ~6G freed, 0 errors, no services broken).

Usage:
  1. Fill in ARCHIVE_SOURCES / SPECIAL_ARCHIVE / DELETE_DIRS / DELETE_FILES below.
  2. python3 cleanup_two_phase.py            # ARCHIVE-ONLY (default): copies + drafts manifest
  3. Verify:  test -f <ARCH>/<label>/<keyfile>   (reports / creds present)
  4. test -f <key1> && python3 cleanup_two_phase.py delete   # rmtree + final manifest

Never run `delete` before a successful archive pass.
"""
import os
import shutil
import sys
from datetime import datetime

# ----------------------------- EDIT ME -----------------------------
ARCH = "/root/reports/old-campaigns"   # archive root; tune for your host
MANIFEST = "/root/deep-cleanup-manifest-%s.md" % datetime.now().strftime("%Y%m%d")
MAX_FILE = 256 * 1024          # per-file cap for archiving
MAX_TOTAL = 130 * 1024 * 1024  # total archive cap

ARCHIVE_SOURCES = [            # (src_dir, archive_label)
    # ("/root/sf8709-pentest", "sf8709"),
]
DELETE_DIRS = [                # dirs to rmtree after archiving
    # "/root/sf8709-pentest",
]
DELETE_FILES = [               # single junk files
    # "/root/hydra.restore", "/root/.hermes/state.db.corrupt_123",
]
SPECIAL_ARCHIVE = [            # (src_dir, label, filter_fn(rel, ext) -> bool); e.g. audit scripts only
    # ("/root/source-dump", "src-audit",
    #  lambda rel, ext: rel.startswith("audit") or "readme" in rel.lower()),
]
SKIP_EXT = {"jpg", "jpeg", "png", "gif", "webp", "ico", "bmp", "svg", "zip", "tar", "gz",
            "tgz", "7z", "rar", "db", "sqlite", "sqlite3", "dump", "sql", "exe", "so",
            "bin", "pyc", "class", "jar", "apk", "mp3", "mp4", "wav", "onnx", "pt",
            "pkl", "img", "iso", "deb", "rpm", "node", "map"}
# -------------------------------------------------------------------


def dsize(path):
    total = 0
    for dp, dn, fn in os.walk(path):
        for f in fn:
            fp = os.path.join(dp, f)
            try:
                if not os.path.islink(fp):
                    total += os.lstat(fp).st_size
            except OSError:
                pass
    return total


def human(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return "%d%s" % (n, unit)
        n /= 1024.0
    return "%.1fT" % n


def archive_dir(src, label, filt=None):
    """Copy <=MAX_FILE non-binary files (recursive, depth<=5) into ARCH/label."""
    dest = os.path.join(ARCH, label)
    n = total = skipped = 0
    for dp, dn, fn in os.walk(src):
        if dp[len(src):].count(os.sep) >= 5:
            dn[:] = []
            continue
        for f in fn:
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, src)
            try:
                if os.path.islink(fp) or not os.path.isfile(fp):
                    continue
                st = os.lstat(fp)
            except OSError:
                continue
            ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
            if ext in SKIP_EXT:
                skipped += 1
                continue
            if filt and not filt(rel, ext):
                continue
            if st.st_size > MAX_FILE or total + st.st_size > MAX_TOTAL:
                skipped += 1
                continue
            out = os.path.join(dest, rel)
            try:
                os.makedirs(os.path.dirname(out) or dest, exist_ok=True)
                shutil.copy2(fp, out)
                n += 1
                total += st.st_size
            except OSError:
                skipped += 1
    return n, total, skipped


def main():
    lines = ["# Deep cleanup -- %s" % datetime.now().strftime("%Y-%m-%d %H:%M"), "", "## Archive"]
    for src, label in ARCHIVE_SOURCES:
        if not os.path.isdir(src):
            lines.append("- %s: [missing, skip]" % label)
            continue
        n, total, sk = archive_dir(src, label)
        lines.append("- %s: %d files / %s (%d skipped)" % (label, n, human(total), sk))
        print("[arch] %s: %d files %s" % (label, n, human(total)))
    for src, label, filt in SPECIAL_ARCHIVE:
        if os.path.isdir(src):
            n, total, sk = archive_dir(src, label, filt)
            lines.append("- %s (filtered): %d files / %s" % (label, n, human(total)))
            print("[arch] %s: %d files %s" % (label, n, human(total)))

    if "delete" not in sys.argv:
        lines += ["", "## [archive-only] no deletions performed"]
        with open(MANIFEST, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        print("\narchive-only mode; no deletions. manifest -> %s" % MANIFEST)
        return 0

    errs = []
    freed = 0
    lines += ["", "## Deleted (dirs)"]
    for d in DELETE_DIRS:
        if not os.path.exists(d):
            lines.append("- %s: [gone already]" % d)
            continue
        sz = dsize(d)
        try:
            shutil.rmtree(d)
            freed += sz
            lines.append("- %s: %s" % (d, human(sz)))
            print("[rm] %s %s" % (d, human(sz)))
        except Exception as e:  # noqa: BLE001 - log and continue
            errs.append("%s: %s" % (d, e))
            lines.append("- %s: **FAILED** %s" % (d, e))
    lines += ["", "## Deleted (files)"]
    for f in DELETE_FILES:
        if not os.path.exists(f):
            lines.append("- %s: [gone already]" % f)
            continue
        try:
            sz = os.path.getsize(f)
            os.remove(f)
            freed += sz
            lines.append("- %s: %s" % (f, human(sz)))
            print("[rm] %s %s" % (f, human(sz)))
        except Exception as e:  # noqa: BLE001
            errs.append("%s: %s" % (f, e))
            lines.append("- %s: **FAILED** %s" % (f, e))
    lines += ["", "## TOTAL freed ~%s; errors %d" % (human(freed), len(errs))]
    with open(MANIFEST, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\nTOTAL freed ~%s; errors=%d" % (human(freed), len(errs)))
    print("manifest -> %s" % MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
