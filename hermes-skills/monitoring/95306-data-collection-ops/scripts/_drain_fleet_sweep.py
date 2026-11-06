#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""95306 采集机队 drain 当日口径 sweep(经主服 paramiko 跳转)
用法: python _drain_fleet_sweep.py            # 全 12 台当日 入队/榨干/跳过 + 账本 pending
      python _drain_fleet_sweep.py win 上海 成都2  # 指定台取 09:00 起 drain/榨干/候选 原文
依赖: paramiko 在 `python` 3.11(不是 python3)
关键坑(09-15 实证):
  1) 老8台日志在 journald(-u v6collector),新4台(sh8-11)只在 /opt/v6/v6_run.log 且**无 journald 单位**
     → 判分支必须看**内容**为空,不能只看 journalctl 退出码(退出码 0+空输出会把新4台误读成当日 0)
  2) grep -c 对空串会算 1 → 一律 echo "$E" | grep -ac
"""
import paramiko, os, base64, sys

MASTER = ("128.241.245.73", 12971)
KEY = os.path.expanduser(r"~/.ssh/v6_master_key")
MACHINES = [
    ("上海", "8.133.188.178", 0), ("杭州", "121.43.97.73", 1),
    ("广州", "8.138.236.124", 2), ("成都", "47.108.152.60", 3),
    ("上海2", "8.133.212.134", 4), ("成都2", "47.108.173.230", 5),
    ("青岛", "47.104.139.212", 6), ("深圳", "47.107.124.62", 7),
    ("上海3", "47.103.86.92", 8), ("武汉", "8.148.7.168", 9),
    ("乌兰察布", "8.130.171.221", 10), ("河源", "47.120.9.89", 11),
]

SWEEP = r'''
D=$(date +%m-%d)
# 09-15 13:2x 修: 原逻辑「journalctl 非空即 journald」→ sh9/sh11 journald 非空但无应用行 ⇒ 误报 入队=0 榨干=0。
# 改为 journald ∪ 文件 归一化(去 journal 前缀)后 sort -u 去重, 两路各查。
J=$(journalctl -u v6collector --no-pager --since today 2>/dev/null | grep -aE 'drain 入队|榨干队列|跳过\(分片\)')
F=$(tail -60000 /opt/v6/v6_run.log 2>/dev/null | grep -aF "[$D " | grep -aE 'drain 入队|榨干队列|跳过\(分片\)')
A=$(printf '%s\n%s\n' "$J" "$F" | sed 's/^.*python3\[[0-9]*\]: //' | grep -av '^$' | sort -u)
echo "SRC=J$(echo "$J" | grep -ac .)/F$(echo "$F" | grep -ac .) SKIP=$(echo "$A" | grep -ac '跳过(分片)') 入队=$(echo "$A" | grep -ac 'drain 入队') 榨干=$(echo "$A" | grep -ac '榨干队列')"
echo "LASTQ=$(echo "$A" | grep -a 'drain 入队' | tail -1)"
echo "LASTZ=$(echo "$A" | grep -a '榨干队列' | tail -1)"
echo "VERS=$(md5sum /opt/v6/collector.py | cut -c1-32) $(stat -c %y /opt/v6/collector.py | cut -c1-19) START=$(systemctl show v6collector -p ExecMainStartTimestamp | cut -d= -f2)"
echo "KEYS=$(echo "$A" | grep -ao 'drain 入队 \S*' | awk '{print $3}' | sort -u | tr '\n' ',')"
S=""
for p in /tmp/v6_state.json /opt/v6/v6_state.json /opt/v6/state.json /data_raw/v6_state.json; do [ -f "$p" ] && S="$p" && break; done
echo "STPATH=$S"
[ -n "$S" ] && python3 - "$S" <<'PYEOF'
import json,sys
s=json.load(open(sys.argv[1]))
d=s.get('drain',{})
proj=sum(len(v.get('all',[])) for v in d.values())
pend=sum(len([x for x in v.get('all',[]) if x not in v.get('done',[])]) for v in d.values())
print('DRAIN acct=%d proj=%d pend=%d seen=%d cd=%s' % (len(d),proj,pend,len(s.get('seen_st',{})),s.get('cooldown_until')))
for k,v in d.items():
    un=[x for x in v.get('all',[]) if x not in v.get('done',[])]
    if un: print('  PEND %s proj=%s done=%s' % (k,len(v.get('all',[])),len(v.get('done',[]))))
PYEOF
'''

WIN = r'''
journalctl -u v6collector --no-pager --since "2026-09-15 09:00:00" 2>/dev/null | grep -aE "drain 入队|榨干队列|跳过\(分片\)|候选 [1-9]|轮询完成|识别 [1-9]" | tail -25
'''


def run(m, ip, remote, t=90):
    cmd = "echo %s | base64 -d | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@%s bash -s" % (
        base64.b64encode(remote.encode()).decode(), ip)
    _, o, e = m.exec_command(cmd, timeout=t)
    return o.read().decode(errors="replace").strip(), e.read().decode(errors="replace").strip()


def main():
    m = paramiko.SSHClient()
    m.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    m.connect(MASTER[0], port=MASTER[1], username="root", key_filename=KEY, timeout=30)
    want = sys.argv[2:] if len(sys.argv) > 2 else None
    for nm, ip, sh in MACHINES:
        if want and nm not in want:
            continue
        try:
            o, e = run(m, ip, WIN if (len(sys.argv) > 1 and sys.argv[1] == "win") else SWEEP)
        except Exception as ex:
            o, e = "", str(ex)
        print("## %s sh%d (%s)" % (nm, sh, ip))
        print(o if o else "ERR " + e[:200])
    m.close()


if __name__ == "__main__":
    main()
