#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload a big file to GoFile (no account needed); print download page + md5 check.

Usage:  python gofile_upload.py <file>
Validated 2026-10 with a 554MB archive (~40s on a fast pipe).
Free/anonymous files may be purged when idle for long -> tell the user to re-download/save.
"""
import sys, hashlib, requests


def main():
    path = sys.argv[1]
    r = requests.get("https://api.gofile.io/servers", timeout=30)
    srv = r.json()["data"]["servers"][0]["name"]
    print("server:", srv)
    with open(path, "rb") as f:
        r2 = requests.post(f"https://{srv}.gofile.io/contents/uploadfile",
                           files={"file": f}, timeout=3600)
    j = r2.json()
    if j.get("status") != "ok":
        print("upload failed:", str(j)[:300])
        return 1
    d = j["data"]
    local_md5 = hashlib.md5(open(path, "rb").read()).hexdigest()
    print("downloadPage:", d["downloadPage"])
    print("name:", d["name"], "size:", d["size"])
    print("md5 local :", local_md5)
    print("md5 server:", d.get("md5"))
    print("MATCH" if local_md5 == d.get("md5") else "MISMATCH - re-upload before sharing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
