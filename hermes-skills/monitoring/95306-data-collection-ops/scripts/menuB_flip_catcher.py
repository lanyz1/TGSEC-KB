# -*- coding: utf-8 -*-
"""菜单B 抖动捕翻器（跑在主服；定位 /data_pool/<pid>/pack_map.json 的两版本交替）

用法（主服上）：
  python3 -u menuB_flip_catcher.py <PID> [分钟数] [采样秒]
  python3 -u menuB_flip_catcher.py <PID> --diff      # 相邻两版快照字段级 diff

推荐跑法（经跳板机，避免通道被抄导致输出丢失）：
  setsid nohup python3 -u /tmp/menuB_flip_catcher.py <PID> 15 6 > /tmp/flip_out.txt 2>&1 < /dev/null &
  然后短查询： tail -n 40 /tmp/flip_log.txt   （绝不复跑主脚本）

输出：
  /tmp/flip_log.txt   只在 (mtime,size,md5) 变化时打一行（含 通过/拒绝 计数 + 重点账号的包件状态）
  /tmp/flipv_N.json   每次变化存一份完整版本快照（保留最近 20 份）

判读：
  • 窗口 <15 分钟会给「文件根本没翻」的假阴性（翻转是间歇触发）
  • 看到 okX→okY 的跳变后，用该行的 mt 取时间戳，反查同刻写入方（merger cycle / audit_changed / 8515 回写）
  • --diff 会横向列出两版差异的 账号/packCode/审核状态/审核码/审核时间 ⇒ 这就是「另一个版本」的完整身份
"""
import json, os, sys, time, hashlib, glob

PID = sys.argv[1] if len(sys.argv) > 1 else ''
if not PID or PID.startswith('--'):
    print(__doc__)
    sys.exit(1)
if PID == '--diff' or (len(sys.argv) > 2 and sys.argv[2] == '--diff'):
    pass
PM = '/data_pool/' + PID + '/pack_map.json'
LOG = '/tmp/flip_log.txt'
SNAP = '/tmp/flipv_'
WATCH_ACCT = os.environ.get('WATCH_ACCT', '')  # 可指定重点账号/单位关键字

def counts(d):
    ok = rej = wait = 0
    for k, v in (d.get('enterprises') or {}).items():
        for p in (v.get('包件') or []):
            s = str(p.get('审核状态') or '')
            if s == '通过': ok += 1
            elif s == '拒绝': rej += 1
            elif s == '未审批': wait += 1
    return ok, rej, wait

def focus(d):
    out = []
    for k, v in (d.get('enterprises') or {}).items():
        if WATCH_ACCT and WATCH_ACCT not in str(k) and WATCH_ACCT not in str(v.get('单位') or ''):
            continue
        for p in (v.get('包件') or []):
            s = str(p.get('审核状态') or '')
            if s in ('通过', '拒绝'):
                out.append(str(k)[:14] + '/' + str(p.get('packCode')) + '=' + s + '/' + str(p.get('审核码') or ''))
    return ' '.join(sorted(out)[:12])

def do_diff():
    fs = sorted(glob.glob(SNAP + '*.json'), key=lambda f: int(f.split('_')[-1].split('.')[0]))
    if len(fs) < 2:
        print('快照不足 2 份:', fs)
        return
    a, b = fs[-2], fs[-1]
    da = json.load(open(a, encoding='utf-8'))
    db = json.load(open(b, encoding='utf-8'))
    print('DIFF', os.path.basename(a), '->', os.path.basename(b))
    pa, pb = da.get('enterprises') or {}, db.get('enterprises') or {}
    for k in sorted(set(pa) | set(pb)):
        ea, eb = pa.get(k) or {}, pb.get(k) or {}
        ma = {str(p.get('packCode')): p for p in (ea.get('包件') or [])}
        mb = {str(p.get('packCode')): p for p in (eb.get('包件') or [])}
        for pc in sorted(set(ma) | set(mb)):
            x, y = ma.get(pc) or {}, mb.get(pc) or {}
            if (x.get('审核状态'), x.get('审核码')) != (y.get('审核状态'), y.get('审核码')):
                print(' ', k, '/', str(ea.get('单位') or eb.get('单位') or '')[:16], '| pack', pc,
                      '|', x.get('审核状态'), x.get('审核码'), str(x.get('审核时间') or '')[-8:],
                      '->', y.get('审核状态'), y.get('审核码'), str(y.get('审核时间') or '')[-8:])
    print('DIFF DONE')

if '--diff' in sys.argv:
    do_diff()
    sys.exit(0)

MINS = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
STEP = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
N = int(MINS * 60 / STEP)
prev = None
n = 0
snaps = []
with open(LOG, 'a', encoding='utf-8') as lg:
    lg.write(time.strftime('%H:%M:%S') + ' WATCH START ' + PM + ' N=' + str(N) + '\n')
    lg.flush()
    for _ in range(N):
        try:
            st = os.stat(PM)
            raw = open(PM, 'rb').read()
            h = hashlib.md5(raw).hexdigest()[:8]
            if (int(st.st_mtime), st.st_size, h) != prev:
                d = json.loads(raw.decode('utf-8'))
                ok, rej, wait = counts(d)
                lg.write(time.strftime('%H:%M:%S') + ' CH mt' + str(int(st.st_mtime)) + ' sz' + str(st.st_size)
                         + ' h' + h + ' ok' + str(ok) + ' rej' + str(rej) + ' wait' + str(wait)
                         + ' | ' + focus(d) + '\n')
                lg.flush()
                n += 1
                fp = SNAP + str(n) + '.json'
                open(fp, 'wb').write(raw)
                snaps.append(fp)
        except Exception as ex:
            lg.write(time.strftime('%H:%M:%S') + ' ERR ' + str(ex)[:70] + '\n')
            lg.flush()
        time.sleep(STEP)
    lg.write('DONE n=' + str(n) + ' snaps: ' + ' '.join(snaps[-10:]) + '\n')
print('flip_catcher done, variants=' + str(n) + ', log=' + LOG)
