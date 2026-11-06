#!/usr/bin/env python3
"""Classify Aliyun OSS buckets: region mismatch, listing ACL, anonymous object read.

Usage: python3 oss_bucket_classify.py bucket1 bucket2 ...
Only Aliyun OSS endpoints are probed. S3/GCS need their own endpoint map.
"""
import re
import sys
import uuid

import requests

REGIONS = [
    "cn-beijing", "cn-hangzhou", "cn-shanghai", "cn-shenzhen",
    "cn-zhangjiakou", "cn-chengdu", "cn-hongkong",
    "eu-central-1", "ap-southeast-1", "us-west-1",
]


def get(url, timeout=6):
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=False)
        return r.status_code, r.text[:3000]
    except Exception as exc:  # noqa: BLE001 - probe tool, report and continue
        return None, str(exc)[:120]


def code_of(body):
    m = re.search(r"<Code>([^<]+)</Code>", body)
    return m.group(1) if m else ""


def endpoint_of(body):
    m = re.search(r"<Endpoint>([^<]+)</Endpoint>", body)
    return m.group(1) if m else ""


def probe(bucket):
    key = "probe_" + uuid.uuid4().hex + ".sql"
    for region in REGIONS:
        host = f"{bucket}.oss-{region}.aliyuncs.com"
        status, body = get(f"https://{host}/{key}")
        if status is None:
            continue
        code = code_of(body)
        if code == "NoSuchBucket":
            continue
        if code == "NoSuchKey":
            print(f"[PUBLIC-OBJECT] {bucket} @ {region}: random key -> NoSuchKey")
            lstatus, lbody = get(f"https://{host}/?prefix=")
            print(f"  list: {lstatus} {code_of(lbody) or 'OK'}")
            return
        if "specified endpoint" in body:
            endpoint = endpoint_of(body)
            print(f"[REGION-MISMATCH] {bucket} @ {region} -> {endpoint or '?'}")
            if endpoint:
                host2 = f"{bucket}.{endpoint}"
                s2, b2 = get(f"https://{host2}/{key}")
                s3, b3 = get(f"https://{host2}/?prefix=")
                print(f"  object: {s2} {code_of(b2) or 'OK'}; list: {s3} {code_of(b3) or 'OK'}")
                if code_of(b2) == "NoSuchKey":
                    print("  -> object-public: deterministic key guessing is worthwhile")
            return
        if "PublicEndpointForbidden" in body:
            print(f"[CNAME-ONLY] {bucket} @ {region}: PublicEndpointForbidden (use bound custom domain)")
            return
        if "Anonymous user has no right" in body or code == "AccessDenied":
            print(f"[EXISTS/PRIVATE-LIST] {bucket} @ {region}: {status} {code}")
            return
        print(f"[EXISTS] {bucket} @ {region}: {status} {code or body[:100]}")
        return
    print(f"[NOT-FOUND] {bucket}: NoSuchBucket in all probed regions")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    for name in sys.argv[1:]:
        probe(name)
