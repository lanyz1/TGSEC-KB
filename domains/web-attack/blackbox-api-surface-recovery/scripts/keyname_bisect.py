#!/usr/bin/env python3
"""Recover an unknown JSON field name from a black-box API via the all-keys + bisect oracle.

Idea: the server names its next missing field in an error string. Send the whole candidate set at
once; if the "missing" message disappears, bisect the set to isolate the exact key in O(log n).

Usage:
  python3 keyname_bisect.py \
    --url https://api.example.com/api/index/register \
    --base '{"mobile":"13800138000","name":"test","password":"Test123456"}' \
    --keys keys.txt \
    --missing '请输入邀请码' \
    --value 888888 \
    --header 'Authorization: Bearer <token>' \
    --header 'X-App-Version: 9.9.9'

Exit codes: 0 found, 2 none of the candidates advanced the message, 3 transport error.
"""
import argparse, json, re, sys, time, urllib.request, urllib.error

def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('--url', required=True)
    p.add_argument('--base', default='{}', help='base JSON body (all already-known required fields)')
    p.add_argument('--keys', required=True, help='file with one candidate key per line')
    p.add_argument('--missing', default='', help='regex that means "field still missing"')
    p.add_argument('--hit', default='', help='regex that means "advanced" (overrides --missing)')
    p.add_argument('--value', default='888888', help='placeholder value for every candidate key')
    p.add_argument('--header', action='append', default=[], help='Header: value (repeatable)')
    p.add_argument('--timeout', type=float, default=10.0)
    p.add_argument('--delay', type=float, default=0.0)
    p.add_argument('--verbose', action='store_true')
    return p

def main():
    a = build_parser().parse_args()
    base = json.loads(a.base)
    keys = [l.strip() for l in open(a.keys, encoding='utf-8', errors='ignore') if l.strip()]
    if not keys:
        print('empty candidate list'); return 2
    headers = {'Content-Type': 'application/json'}
    for h in a.header:
        if ':' in h:
            k, v = h.split(':', 1); headers[k.strip()] = v.strip()
    calls = {'n': 0}

    def probe(fieldset):
        body = dict(base)
        for k in fieldset:
            body[k] = a.value
        data = json.dumps(body, ensure_ascii=False).encode()
        for attempt in (0, 1):
            try:
                req = urllib.request.Request(a.url, data=data, headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=a.timeout) as r:
                    txt = r.read().decode('utf-8', 'ignore')
                calls['n'] += 1
                if a.delay: time.sleep(a.delay)
                if a.verbose:
                    print(f'  [{calls["n"]}] {len(fieldset)} keys -> {txt[:120]}', file=sys.stderr)
                return txt
            except urllib.error.HTTPError as e:
                txt = e.read().decode('utf-8', 'ignore')
                calls['n'] += 1
                return txt
            except Exception as e:
                if attempt: raise
                time.sleep(1)

    def advanced(fieldset):
        txt = probe(fieldset)
        if a.hit:
            return bool(re.search(a.hit, txt))
        if a.missing:
            return not re.search(a.missing, txt)
        raise SystemExit('need --missing or --hit')

    try:
        if not advanced(keys):
            print(f'NO KEY in set of {len(keys)} (after {calls["n"]} requests)')
            print('hint: the value itself may be rejected, or a partner key is required')
            return 2
        cur = keys
        while len(cur) > 1:
            mid = len(cur) // 2
            left, right = cur[:mid], cur[mid:]
            if advanced(left):
                cur = left
            elif advanced(right):
                cur = right
            else:
                singles = [k for k in cur if advanced([k])]
                print('KEY(S) (partner-dependent, linear fallback):', singles)
                return 0 if singles else 2
        print(f'KEY: {cur[0]}  (requests: {calls["n"]})')
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print('transport error:', e); return 3

if __name__ == '__main__':
    sys.exit(main())
