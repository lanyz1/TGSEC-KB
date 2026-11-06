#!/usr/bin/env python3
"""Host-differential vhost prober — the md5 control for CDN-origin hunting.

Decides, per candidate IP:port, whether a Host-header response is:

  VHOST_MATCH       stable body that DIFFERS from the control Host and does not echo the Host  -> next: fingerprint
  DEFAULT_SITE      stable body IDENTICAL to the control Host                                  -> irrelevant, whatever it says
  REFLECTION        body differs only because it echoes the request Host (dynamic content)      -> irrelevant
  DYNAMIC           the SAME Host gives different bodies across repeats (LB / random content)   -> inconclusive
  HTTP_500          empty-bodied 500 with a PHP default content-type (an origin that answers)    -> report separately

A naive `grep <target>` over a Host spray conflates all of these. Three traps this exists to kill:

  1. Host reflection  — ZBlog/CMS emit <link rel=canonical href="http://<host>:443/"> and CDN
     "domain not bound" pages print the request Host (and YOUR egress IP) into the body.
  2. Faint length deltas — a ~5-byte difference is a dynamic timestamp, not a vhost.
  3. LB backends — a one-off hit that will not reproduce. Hence --repeat.

And for a CDN-fronted URL (--through-cf): `cf-cache-status: HIT` means the bytes are the CDN's, NOT
the origin's. Compare the plain fetch against a cache-busted one before calling anything an origin
fingerprint.

Usage
-----
  # sweep a /24 for a target vhost (plain HTTP: no SNI question)
  python3 host_differential_probe.py --segment 154.12.21.0/24 --host tlgramhq.com

  # probe specific IPs over HTTPS with correct SNI (Trap 1: --resolve, never -H Host)
  python3 host_differential_probe.py --ips-file ips.txt --host t.com --https --path /index.html

  # is a CDN-served asset actually served by the origin?
  python3 host_differential_probe.py --through-cf https://t.com/static/assets/apple-touch-icon.png

Stdlib only. curl is used for the requests.
"""

import argparse
import concurrent.futures
import hashlib
import random
import re
import socket
import string
import subprocess
import sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def rand_host():
    return "".join(random.choices(string.ascii_lowercase, k=12)) + ".invalid-test.invalid"


def curl(url, host=None, resolve=None, timeout=10):
    """Return (status, body_bytes). resolve=(host,port,ip) sets SNI+Host properly."""
    cmd = ["curl", "-s", "-k", "-m", str(timeout), "-A", UA, "-o", "-",
           "-w", "\n__C__%{http_code}__L__%{size_download}"]
    if resolve:
        h, p, ip = resolve
        cmd += ["--resolve", f"{h}:{p}:{ip}"]
    elif host:
        cmd += ["-H", f"Host: {host}"]
    cmd.append(url)
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout + 6).stdout
    except Exception:
        return None, b""
    if b"__C__" not in out:
        return None, b""
    body, meta = out.rsplit(b"\n__C__", 1)
    try:
        code = int(meta.split(b"__L__")[0])
    except Exception:
        code = None
    return code, body


def tcp_open(ip, port, tmo=3.0):
    try:
        s = socket.create_connection((ip, port), timeout=tmo)
        s.close()
        return True
    except Exception:
        return False


def expand(segment):
    base = segment.split("/")[0].rsplit(".", 1)[0]
    return [f"{base}.{i}" for i in range(1, 255)]


def classify(target, path, ip, port, https, repeat, control_host):
    """Run the control experiment for one candidate."""
    if https:
        url_t = f"https://{target}:{port}{path}"
        url_c = f"https://{control_host}:{port}{path}"
        res_t = curl(url_t, resolve=(target, port, ip))
        res_c = curl(url_c, resolve=(control_host, port, ip))
    else:
        scheme = "https" if port == 443 else "http"
        def go(h):
            return curl(f"{scheme}://{ip}:{port}{path}", host=h)
        res_t = go(target)
        res_c = go(control_host)

    code_t, body_t = res_t
    code_c, body_c = res_c
    if code_t is None:
        return ip, port, "UNREACHABLE", "", ""

    # stability: same Host, several times
    bodies = [body_t]
    for _ in range(max(0, repeat - 1)):
        if https:
            _, b = curl(f"https://{target}:{port}{path}", resolve=(target, port, ip))
        else:
            scheme = "https" if port == 443 else "http"
            _, b = curl(f"{scheme}://{ip}:{port}{path}", host=target)
        bodies.append(b)
    stable = len({hashlib.md5(b).hexdigest() for b in bodies}) == 1

    if code_t == 500 and len(body_t) == 0:
        return ip, port, "HTTP_500", code_t, "empty 500 — origin answers, app broken"
    if not stable:
        return ip, port, "DYNAMIC", code_t, "same Host gave different bodies -> LB/random content"

    md5_t = hashlib.md5(body_t).hexdigest()
    md5_c = hashlib.md5(body_c or b"").hexdigest()
    echoes = target.encode().lower() in body_t.lower()

    if md5_t == md5_c:
        return ip, port, "DEFAULT_SITE", code_t, f"identical to control Host ({len(body_t)} B)"
    if echoes:
        # differs, but the target string is in the body -> assume reflection; confirm the delta is the Host
        return ip, port, "REFLECTION", code_t, "body echoes the request Host — fingerprint junk"
    delta = len(body_t) - len(body_c or b"")
    if abs(delta) <= 8:
        return ip, port, "DEFAULT_SITE", code_t, f"delta {delta} B <= noise floor"
    return ip, port, "VHOST_MATCH", code_t, f"len={len(body_t)} vs {len(body_c or b'')} — fingerprint this"


def through_cf(url, repeat=2):
    """Compare a plain fetch against a cache-busted one. HIT => bytes are the CDN's, not the origin's."""
    sep = "&" if "?" in url else "?"
    stat = re.compile(rb"cf-cache-status:\s*([A-Za-z]+)", re.I)

    def fetch(u):
        r = subprocess.run(["curl", "-s", "-k", "-m", "15", "-D", "-", "-A", UA, "-o", "-", u],
                           capture_output=True, timeout=25).stdout
        head, _, body = r.partition(b"\r\n\r\n")
        m = stat.search(head)
        return (m.group(1).decode().upper() if m else "?"), hashlib.md5(body).hexdigest()[:12], len(body)

    plain = fetch(url)
    busted = fetch(f"{url}{sep}cb={random.randint(10**8, 10**9)}")
    print(f"plain : cf-cache={plain[0]:8s} md5={plain[1]} len={plain[2]}")
    print(f"busted: cf-cache={busted[0]:8s} md5={busted[1]} len={busted[2]}")
    if plain[0] == "HIT" and plain[1] != busted[1]:
        print("  -> CACHED COPY DIFFERS FROM ORIGIN: the plain fetch is a cache reading, not the origin's.")
    elif plain[0] == "HIT" and busted[1].startswith("?"):
        print("  -> HIT; origin fetch failed — treat the cached bytes as unproven origin evidence.")
    else:
        print("  -> both reached the origin (or both cached); compare the two bodies directly.")


def main():
    ap = argparse.ArgumentParser(description="Host-differential vhost prober (md5 control).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--segment", help="e.g. 154.12.21.0/24")
    src.add_argument("--ips-file", help="one IP per line")
    src.add_argument("--through-cf", help="a CDN-fronted URL: cache-bust comparison only")
    ap.add_argument("--host", help="target hostname (required for segment/ips modes)")
    ap.add_argument("--control-host", help="control Host (default: a random .invalid name)")
    ap.add_argument("--path", default="/")
    ap.add_argument("--ports", default="80,443")
    ap.add_argument("--https", action="store_true",
                    help="use --resolve (correct SNI+Host) instead of -H Host")
    ap.add_argument("--repeat", type=int, default=2, help="same-Host repeats for the stability check")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    if args.through_cf:
        through_cf(args.through_cf)
        return 0
    if not args.host:
        ap.error("--host is required with --segment/--ips-file")

    ips = expand(args.segment) if args.segment else [l.strip() for l in open(args.ips_file) if l.strip()]
    ports = [int(p) for p in args.ports.split(",")]
    control = args.control_host or rand_host()

    print(f"[*] {len(ips)} IPs x {ports}  target={args.host}  control={control}  path={args.path}", flush=True)
    live = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=128) as ex:
        for ip, port, ok in ex.map(lambda t: (t[0], t[1], tcp_open(*t)),
                                   [(ip, p) for ip in ips for p in ports]):
            if ok:
                live.append((ip, port))
    print(f"[+] open {len(live)}", flush=True)

    hits = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for ip, port, verdict, code, note in ex.map(
                lambda t: classify(args.host, args.path, t[0], t[1], args.https, args.repeat, control), live):
            if verdict in ("DEFAULT_SITE", "REFLECTION", "DYNAMIC"):
                continue  # noise: say nothing unless asked
            print(f"  {verdict:12s} {ip}:{port} code={code} {note}", flush=True)
            hits.append((ip, port, verdict))

    print(f"\n[=] candidates: {hits if hits else 'none'}")
    print("[i] VHOST_MATCH => fingerprint (title / favicon md5 / custom icon / Last-Modified) before claiming origin.")
    print("[i] HTTP_500 empty body => an origin that answers; keep it as a lead even without an IP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
