#!/usr/bin/env python3
"""List operations with no security requirement from an OpenAPI 3 spec.

Usage: python3 openapi_anon.py openapi.json
"""
import json
import sys


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    spec = json.load(open(path, encoding="utf-8"))
    global_security = spec.get("security", [])
    print(f"global security: {global_security}")
    anon = []
    for route, ops in spec.get("paths", {}).items():
        for method, op in ops.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            if not op.get("security", global_security):
                anon.append((method.upper(), route, op.get("summary", ""), op.get("tags")))
    print(f"anonymous endpoints: {len(anon)}")
    for method, route, summary, tags in anon:
        print(f"{method:6} {route:55} {summary[:45]:47} {tags}")


if __name__ == "__main__":
    main()
