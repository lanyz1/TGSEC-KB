#!/usr/bin/env python3
"""Anonymous full listing of an S3 / OSS / COS-compatible bucket (ListObjectsV2 pagination).

Usage:
    python3 list_bucket.py <bucket-host> <out.txt> [prefix]

    <bucket-host>  e.g. ossimagebu009.oss-cn-hongkong.aliyuncs.com
                        my-bucket.s3.amazonaws.com
                        mybucket.cos.ap-hongkong.myqcloud.com
    <out.txt>      one key per line, APPENDED page by page (safe to re-run)
    [prefix]       optional. OMIT for the true full listing -- an app-inherited
                   prefix under-reports by orders of magnitude.

Progress goes to stderr; keys go only to <out.txt>.
Exit 0 = completed (IsTruncated false), 2 = listing denied, 3 = network error.
"""
import sys
import ssl
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

MAX_KEYS = 1000


def local(el):
    return el.tag.split("}")[-1]


def first_text(root, name):
    for el in root.iter():
        if local(el) == name:
            return el.text
    return None


def list_page(host, token, prefix, ctx):
    q = {"list-type": "2", "max-keys": str(MAX_KEYS)}
    if prefix:
        q["prefix"] = prefix
    if token:
        q["continuation-token"] = token
    url = "https://%s/?%s" % (host, urllib.parse.urlencode(q))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return ET.fromstring(r.read())


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    host, out = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else ""

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    token = None
    total = 0
    page = 0
    with open(out, "a", encoding="utf-8") as f:
        while True:
            try:
                root = list_page(host, token, prefix, ctx)
            except urllib.error.HTTPError as e:
                print("[!] HTTP %s: %s" % (e.code, e.read()[:200]), file=sys.stderr)
                return 2
            except Exception as e:  # noqa: BLE001 - report and stop
                print("[!] %s" % e, file=sys.stderr)
                return 3

            keys = [el.text for el in root.iter() if local(el) == "Key" and el.text]
            for k in keys:
                f.write(k + "\n")
            f.flush()
            total += len(keys)
            page += 1

            trunc = (first_text(root, "IsTruncated") or "false").strip().lower() == "true"
            print("[page %d] +%d  total=%d  truncated=%s" % (page, len(keys), total, trunc),
                  file=sys.stderr)
            if not trunc:
                print("[done] %d objects -> %s" % (total, out), file=sys.stderr)
                return 0
            token = <REDACTED>, "NextContinuationToken")
            if not token:
                print("[!] truncated but no continuation token; stopping", file=sys.stderr)
                return 4


if __name__ == "__main__":
    sys.exit(main())
