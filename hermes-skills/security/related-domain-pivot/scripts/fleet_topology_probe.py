#!/usr/bin/env python3
"""Fleet topology probe - determine whether sibling hosts share one backend.

Replays ONE authenticated request against every entry and compares identity
fields. Identical id/role across hosts => shared user store, no isolation.

Usage:
    export TOK='<jwt>'
    python3 fleet_topology_probe.py hosts.txt [probe_path]
    python3 fleet_topology_probe.py hosts.txt --anonym

hosts.txt: one host per line; bare host, host:port, or a full URL.
Env: TOK (bearer token). Use --anonym to skip auth and compare whatever
identity-ish field the endpoint returns.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

IDENT_RE = re.compile(
    r'"(id|user_id|uid|role|email|username|site)"\s*:\s*("[^"]*"|[^,}\]]+)'
)
KEEP = ("id", "user_id", "uid", "role", "email", "username", "site")


def probe(host, path, token):
    url = host if host.startswith("http") else "https://" + host
    url = url.rstrip("/") + path
    hdrs = {"User-Agent": "Mozilla/5.0 (compatible; fleet-topology-probe)"}
    if token:
        hdrs["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
            return host, r.status, r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return host, e.code, e.read(20_000).decode("utf-8", "replace")
    except Exception as e:
        return host, -1, f"{type(e).__name__}: {e}"


def identity(body):
    """Pull identity fields out of a JSON body, falling back to a regex scan."""
    out = {}
    try:
        data = json.loads(body)
        node = data.get("data", data) if isinstance(data, dict) else {}
        if isinstance(node, dict):
            for k, v in node.items():
                if k in KEEP and not isinstance(v, (dict, list)):
                    out[k] = v
        if out:
            return out
    except Exception:
        pass
    for k, v in IDENT_RE.findall(body or "")[:8]:
        out.setdefault(k, v.strip().strip('"'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hosts")
    ap.add_argument("path", nargs="?", default="/api/v1/user/profile")
    ap.add_argument("--anonym", action="store_true",
                    help="no token; compare whatever identity field is returned")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    token = "" if a.anonym else os.environ.get("TOK", "")
    if not token and not a.anonym:
        print("warning: TOK unset and no --anonym; results may all be 401",
              file=sys.stderr)

    with open(a.hosts) as fh:
        hosts = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    if not hosts:
        print("no hosts in " + a.hosts, file=sys.stderr)
        return 1

    results = {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for host, code, body in ex.map(lambda h: probe(h, a.path, token), hosts):
            results[host] = (code, identity(body))

    print(f"{'HOST':30} {'CODE':>5}  IDENTITY")
    for host in hosts:
        code, ident = results.get(host, (-1, {}))
        print(f"{host:30} {code:>5}  {json.dumps(ident, ensure_ascii=False)[:88]}")

    live = {h: i for h, (c, i) in results.items() if c == 200 and i}
    sigs = {json.dumps(i, sort_keys=True, ensure_ascii=False) for i in live.values()}

    print("\n--- VERDICT ---")
    if not live:
        print("no entry returned 200 with identity fields; inconclusive")
        print("(check the probe path, the token, and whether a CDN fronts these hosts)")
    elif len(sigs) == 1:
        print(f"SHARED BACKEND: {len(live)}/{len(hosts)} live entries returned an "
              f"IDENTICAL identity")
        print(" => one user store, no isolation; one token reaches all,")
        print("    and an admin compromise on any entry compromises all of them")
    else:
        print(f"SPLIT CLUSTER: {len(sigs)} distinct identities across "
              f"{len(live)} live entries")
        for h, i in live.items():
            print(f"    {h}: {json.dumps(i, ensure_ascii=False)[:80]}")
        print(" => entries are data-isolated; test auth/business per cluster")
    return 0


if __name__ == "__main__":
    sys.exit(main())
