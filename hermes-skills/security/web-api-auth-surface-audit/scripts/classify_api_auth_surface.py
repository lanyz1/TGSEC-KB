#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify the auth surface of an API described by an OpenAPI document.

Implements the two rules that are easiest to get wrong:
  R2  frameworks validate the body BEFORE they evaluate auth, so an empty-body
      probe hides the real gate -> on a 422/400 build a MINIMAL conforming body
      from the spec (resolving $ref) and retry once.
  R1  classify by the error SHAPE, not the status code: a business-validation
      error ("X is required") means the handler ran with NO auth check.

Usage:
  python3 classify_api_auth_surface.py http://host:8001 openapi.json [out.json]

Output: per-operation verdicts, the counts, and a JSON dump for the report.
"""
import json
import sys

import requests

requests.packages.urllib3.disable_warnings()

PROBE = "___probe___"
TYPED = {"string": "probe", "integer": 1, "number": 1.5, "boolean": True}


def deref(spec, node, depth=0):
    """Resolve $ref (bounded) so the caller can inspect the real schema."""
    while isinstance(node, dict) and "$ref" in node and depth < 12:
        cur = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            cur = cur.get(part, {}) if isinstance(cur, dict) else {}
        node, depth = cur, depth + 1
    return node if isinstance(node, dict) else {}


def minimal(spec, schema, depth=0):
    """Build the smallest value that satisfies a schema (required fields only)."""
    s = deref(spec, schema, depth)
    if not s or depth > 8:
        return {}
    for key in ("anyOf", "oneOf", "allOf"):
        if isinstance(s.get(key), list) and s[key]:
            return minimal(spec, s[key][0], depth + 1)
    t = s.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0])
    if t == "object" or (t is None and "properties" in s):
        props = s.get("properties") or {}
        req = s.get("required") or list(props)[:1]
        return {k: minimal(spec, props.get(k, {}), depth + 1) for k in req if k in props or not props}
    if t == "array":
        items = s.get("items")
        return [minimal(spec, items, depth + 1)] if items else []
    return TYPED.get(t, "probe")


def classify(status):
    if status in (401, 403):
        return "GATED"
    if status == 200:
        return "OPEN_DATA"
    if status in (400, 422, 500):
        return "UNAUTH_ERR"      # handler executed -> business logic, no auth check
    if status == 404:
        return "NOT_FOUND"       # probe id absent; the operation itself is ungated
    if status == 405:
        return "METHOD"
    return "OTHER"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    base = sys.argv[1].rstrip("/")
    spec = json.load(open(sys.argv[2], encoding="utf-8"))
    out_path = sys.argv[3] if len(sys.argv) > 3 else "auth_surface_matrix.json"

    sess = requests.Session()
    sess.verify = False
    sess.headers.update({"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    rows = []

    for path, ops in sorted(spec.get("paths", {}).items()):
        for method, op in ops.items():
            url = base + path
            for token in ("{task_id}", "{account_id}", "{file_path}", "{id}", "{key}"):
                url = url.replace(token, PROBE)
            attempts = []
            if method in ("get", "delete", "head"):
                attempts = [None]
            else:
                attempts = [{}]
                rb = op.get("requestBody") or {}
                content = (rb.get("content") or {}).get("application/json") or {}
                schema = content.get("schema")
                if schema:
                    shaped = minimal(spec, schema)
                    if shaped and shaped != {}:
                        attempts.append(shaped)
            verdict, snippet = "UNKNOWN", ""
            for payload in attempts:
                try:
                    if payload is None:
                        r = sess.request(method.upper(), url, timeout=20)
                    else:
                        r = sess.request(method.upper(), url, json=payload, timeout=20)
                except Exception as exc:  # transport failure is NOT a tested state
                    verdict, snippet = "TRANSPORT_ERR", str(exc)[:80]
                    continue
                verdict, snippet = classify(r.status_code), r.text[:160].replace("\n", " ")
                # an empty-body verdict only stands if it already settles the question
                if payload == {} and verdict in ("GATED", "OPEN_DATA", "UNAUTH_ERR"):
                    break
            rows.append({"method": method.upper(), "path": path, "verdict": verdict, "body": snippet})

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("%-7s %-52s %-13s %s" % ("METHOD", "PATH", "VERDICT", "BODY"))
    for r in rows:
        print("%-7s %-52s %-13s %s" % (r["method"], r["path"], r["verdict"], r["body"][:70]))
    print("\n=== counts ===")
    for k in sorted(counts, key=lambda x: -counts[x]):
        print("  %-14s %d" % (k, counts[k]))
    print("\ndriveable without credentials (UNAUTH_ERR + OPEN_DATA):",
          counts.get("UNAUTH_ERR", 0) + counts.get("OPEN_DATA", 0))
    json.dump(rows, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
