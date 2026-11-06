#!/usr/bin/env python3
"""Triple fingerprint gate for CF-hidden static SEO landers.

A candidate passes only when ALL of:
  1) custom icon md5 matches
  2) robots body matches exclusivity (substr and/or exact length)
  3) response has no cf-ray

Also runs catch-all control: same homepage md5 for target Host vs random Host => FAIL.

Usage:
  python3 triple_fp_verify.py --ip 1.2.3.4 --host tlgramhq.com \
    --icon-md5 295ccdb03006b8dfef45090dafbd46ac \
    --robots-substr telegramset.com/sitemap.xml [--robots-len 68]
  python3 triple_fp_verify.py --ip-file ips.txt --host tlgramhq.com ...
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def curl(url: str, host: str | None, timeout: int = 8) -> tuple[str, bytes]:
    args = [
        "curl", "-s", "-k", "-m", str(timeout), "-D", "-", "-o", "/tmp/_tfp_body.bin",
        "-A", "Mozilla/5.0",
    ]
    if host:
        args += ["-H", f"Host: {host}"]
    args.append(url)
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout + 4)
        hdr = r.stdout.decode("utf-8", "ignore")
        try:
            body = open("/tmp/_tfp_body.bin", "rb").read()
        except OSError:
            body = b""
        return hdr, body
    except Exception:
        return "", b""


def code_from(hdr: str) -> str:
    for line in hdr.splitlines():
        if line.upper().startswith("HTTP/"):
            parts = line.split()
            return parts[1] if len(parts) > 1 else "?"
    return "000"


def has_cfray(hdr: str) -> bool:
    return "cf-ray" in hdr.lower()


def probe_one(
    ip: str,
    host: str,
    icon_path: str,
    icon_md5: str,
    robots_substr: str | None,
    robots_len: int | None,
    scheme: str,
    port: int,
) -> dict:
    if port in (80, 443):
        base = f"{scheme}://{ip}"
    else:
        base = f"{scheme}://{ip}:{port}"

    # catch-all control
    hdr_t, body_t = curl(base + "/", host)
    hdr_r, body_r = curl(base + "/", "zzz-tfp-control-999.invalid")
    md_t = hashlib.md5(body_t).hexdigest()
    md_r = hashlib.md5(body_r).hexdigest()
    catch_all = bool(body_t) and md_t == md_r and code_from(hdr_t) not in ("000", "?")

    # icon
    hdr_i, body_i = curl(base + icon_path, host)
    im = hashlib.md5(body_i).hexdigest() if body_i else ""
    icon_ok = im == icon_md5 and code_from(hdr_i).startswith("2")

    # robots
    hdr_rb, body_rb = curl(base + "/robots.txt", host)
    rob_ok = False
    if body_rb and not has_cfray(hdr_rb):
        if robots_len is not None and len(body_rb) != robots_len:
            rob_ok = False
        else:
            rob_ok = True
            if robots_substr:
                rob_ok = robots_substr.encode() in body_rb

    no_cf = not has_cfray(hdr_t) and not has_cfray(hdr_i) and not has_cfray(hdr_rb)
    # homepage may be 500; judge cf on asset responses primarily
    if has_cfray(hdr_i) or has_cfray(hdr_rb):
        no_cf = False

    passed = icon_ok and rob_ok and no_cf and not catch_all
    return {
        "ip": ip,
        "port": port,
        "scheme": scheme,
        "passed": passed,
        "icon_ok": icon_ok,
        "icon_md5": im,
        "robots_ok": rob_ok,
        "robots_len": len(body_rb),
        "no_cf": no_cf,
        "catch_all": catch_all,
        "home_code": code_from(hdr_t),
        "home_len": len(body_t),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ip", action="append", default=[])
    ap.add_argument("--ip-file")
    ap.add_argument("--host", required=True)
    ap.add_argument("--icon-md5", required=True)
    ap.add_argument("--icon-path", default="/static/assets/apple-touch-icon.png")
    ap.add_argument("--robots-substr", default=None)
    ap.add_argument("--robots-len", type=int, default=None)
    ap.add_argument("--scheme", default="https", choices=("http", "https"))
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("-j", type=int, default=20)
    args = ap.parse_args()

    ips = list(args.ip)
    if args.ip_file:
        with open(args.ip_file) as f:
            ips += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    ips = sorted(set(ips))
    if not ips:
        print("no ips", file=sys.stderr)
        return 2

    port = args.port or (443 if args.scheme == "https" else 80)
    hits = []

    def run(ip: str) -> dict:
        return probe_one(
            ip, args.host, args.icon_path, args.icon_md5,
            args.robots_substr, args.robots_len, args.scheme, port,
        )

    with ThreadPoolExecutor(max_workers=args.j) as ex:
        futs = {ex.submit(run, ip): ip for ip in ips}
        for fut in as_completed(futs):
            row = fut.result()
            flag = "PASS" if row["passed"] else "fail"
            print(
                f"[{flag}] {row['ip']}:{row['port']} home={row['home_code']}/{row['home_len']} "
                f"icon={row['icon_ok']}({row['icon_md5'][:12]}) "
                f"robots={row['robots_ok']}(len={row['robots_len']}) "
                f"no_cf={row['no_cf']} catch_all={row['catch_all']}"
            )
            if row["passed"]:
                hits.append(row)

    print(f"# scanned={len(ips)} passed={len(hits)}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
