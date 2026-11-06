#!/usr/bin/env python3
"""AD surface check: DNS SRV + common AD ports, no authentication."""
from __future__ import annotations

import argparse
import json
import socket

PORTS = {53: "dns", 88: "kerberos", 135: "rpc", 139: "netbios", 389: "ldap",
         445: "smb", 464: "kpasswd", 636: "ldaps", 3268: "globalcat", 5985: "winrm-http",
         5986: "winrm-https"}


def check(host: str, timeout: float) -> dict:
    out = {}
    for port, name in PORTS.items():
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            out[str(port)] = name
        except OSError:
            pass
        finally:
            s.close()
    return out


def srv(domain: str) -> dict:
    out = {}
    for name in (f"_ldap._tcp.dc._msdcs.{domain}", f"_kerberos._tcp.{domain}", f"_kpasswd._tcp.{domain}"):
        try:
            out[name] = [{"target": r[3][0], "port": r[3][1]} for r in socket.getaddrinfo(name, None)]
        except OSError:
            out[name] = []
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="AD 面检查：DNS SRV + 端口")
    ap.add_argument("--domain", "-d", help="AD domain")
    ap.add_argument("--host", "-H", help="DC/host IP or name")
    ap.add_argument("--timeout", type=float, default=2.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.domain and not args.host:
        ap.error("--domain or --host required")
    result = {"domain": args.domain, "host": args.host}
    if args.domain:
        result["srv"] = srv(args.domain)
    if args.host:
        result["open_ports"] = check(args.host, args.timeout)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.domain:
            print("SRV:")
            for k, v in result["srv"].items():
                print(f"  {k}: {v}")
        if args.host:
            print(f"open on {args.host}: {result['open_ports']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
