#!/usr/bin/env python3
"""gRPC reflection probe via grpcurl when available."""
from __future__ import annotations

import argparse
import shutil
import subprocess


def main() -> int:
    ap = argparse.ArgumentParser(description="gRPC reflection 探针")
    ap.add_argument("target", help="host:port")
    ap.add_argument("--service")
    ap.add_argument("--plaintext", action="store_true", default=True)
    args = ap.parse_args()
    exe = shutil.which("grpcurl")
    if not exe:
        print("[err] grpcurl missing; install from https://github.com/fullstorydev/grpcurl/releases")
        return 127
    cmd = [exe, "-plaintext", args.target]
    if args.service:
        cmd += ["describe", args.service]
    else:
        cmd += ["list"]
    print("[run]", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
