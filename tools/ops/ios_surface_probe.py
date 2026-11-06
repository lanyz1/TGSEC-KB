#!/usr/bin/env python3
"""iOS static surface probe: WebKit/IOKit/firmware/log markers."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CASES = Path("/root/cases")
MARKERS = {
    "webkit": ["WKWebView", "JSContext", "JavaScriptCore", "WebKit", "JSC", "Safari"],
    "fw": ["IMG4", "IM4P", "iBoot", "DeviceTree", "sep-firmware", "LLB"],
    "lab": ["build", "AKS", "kernel", "panic", "KASLR", "slide"],
    "iokit": ["IOUserClient", "AppleKeyStore", "IOKit", "IOExternalMethod", "IOCommandGate"],
}
STR = re.compile(rb"[\x20-\x7e]{4,}")


def main() -> int:
    ap = argparse.ArgumentParser(description="iOS 静态攻击面探针")
    ap.add_argument("action", choices=["webkit", "fw", "lab", "iokit"], nargs="?", default="webkit")
    ap.add_argument("--path", "-p", required=True)
    ap.add_argument("--case", "-c")
    args = ap.parse_args()
    p = Path(args.path)
    if not p.exists():
        ap.error(f"not found: {p}")
    data = p.read_bytes()[:512 * 1024 * 1024]
    text = b"\n".join(STR.findall(data)).decode("utf-8", errors="replace")
    hits = {m: text.count(m) for m in MARKERS[args.action] if m in text}
    result = {"path": str(p), "mode": args.action, "bytes": len(data), "hits": hits,
              "level": "L2" if len(hits) >= 2 else ("L1" if hits else "L0")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/ios_surface.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
