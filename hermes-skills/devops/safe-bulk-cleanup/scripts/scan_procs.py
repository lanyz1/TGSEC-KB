#!/usr/bin/env python3
"""Kill-safe process finder. Reads /proc directly so it never matches (or kills) itself,
unlike `pkill -f pattern` whose pattern appears in its own command line (exit -15 SIGTERM).

Usage:  python3 scan_procs.py <keyword> [keyword2 ...]

Prints "PID  cmdline" for matches (case-insensitive, OR), or "(no matches)".
Excludes: itself, sibling scan_procs.py runs.
"""
import os
import sys


def main():
    kws = [k.lower() for k in sys.argv[1:]]
    if not kws:
        print("usage: python3 scan_procs.py kw1 [kw2 ...]")
        return 1
    me = os.getpid()
    hits = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == me:
            continue
        try:
            with open("/proc/%d/cmdline" % pid, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        cmd = raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        if not cmd or "scan_procs.py" in cmd:
            continue
        if any(k in cmd.lower() for k in kws):
            hits.append("%d  %s" % (pid, cmd[:220]))
    print("\n".join(hits) if hits else "(no matches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
