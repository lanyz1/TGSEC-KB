#!/usr/bin/env python3
"""Java web surface probe: safe GET/HEAD of common management/doc paths."""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

CASES = Path("/root/cases")
PATHS = [
    "/actuator", "/actuator/health", "/actuator/env", "/actuator/heapdump",
    "/v2/api-docs", "/v3/api-docs", "/swagger-ui/index.html",
    "/druid/index.html", "/error",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Java 管理面/文档面安全探测（只读）")
    ap.add_argument("--url", "-u", required=True, help="authorized base URL")
    ap.add_argument("--case", "-c", required=True, help="case name")
    ap.add_argument("--timeout", type=int, default=8)
    args = ap.parse_args()

    case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
    art = case / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in PATHS:
        url = urljoin(args.url.rstrip("/") + "/", path.lstrip("/"))
        method = "HEAD" if path.endswith("heapdump") else "GET"
        row = {"path": path, "url": url, "method": method, "status": None, "length": None,
               "title": "", "error": ""}
        try:
            req = urllib.request.Request(url, method=method,
                                         headers={"User-Agent": "TGSEC-java-surface/1.0",
                                                  "Range": "bytes=0-2048"})
            with urllib.request.urlopen(req, timeout=args.timeout) as r:
                row["status"] = r.status
                cl = r.headers.get("Content-Length")
                row["length"] = int(cl) if cl and cl.isdigit() else None
                if method == "GET":
                    body = r.read(2048).decode("utf-8", errors="replace")
                    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
                    row["title"] = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
        print(f"{row['status'] or '-':>4} {path:28} {row['title'][:60]}")

    data = {"target": args.url, "checked_at": datetime.now(timezone.utc).isoformat(), "rows": rows}
    (art / "java_surface.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    interesting = [r for r in rows if r["status"] and r["status"] not in (404, 401, 403)]
    print(f"[java] interesting={len(interesting)} -> {art / 'java_surface.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
