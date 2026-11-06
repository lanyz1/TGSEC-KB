#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icc_triage.py -- 挖矿劫持框架(icc / nvpmgr 类)布点只读排查

目标: 在**已授权**主机上只读判定"是否被 icc/nvpmgr 类框架布点",
并按四层持久化逐层列出命中项(便于按层斩断), 全程不修改任何文件、不 kill 进程。

用法:
  python3 icc_triage.py --root /                       # 真实主机(只读)
  python3 icc_triage.py --root /tmp/mock --json        # 靶树/mock
  python3 icc_triage.py --root / --max-depth 5 --max-entries 20000

退出码: 0 = 无命中 / 10 = 有命中 / 2 = 参数或根路径错误
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

MINER_NAMES = (r'krig-miner|xmrig|nbminer|lolminer|trex|srbminer|peakminer|miner2|'
               r'kdevtmpfsi|kinsing|rig3748|rev_tunnel|rev_gate_key|ccminer|'
               r'phoenixminer|gminer|bzminer|xmr-stak|xmr-node-proxy')
FRAMEWORK_MARK = r'nvpmgr|antirival|nvp-mgr|nvpmgript'
CRON_SUSPECT = re.compile(
    MINER_NAMES + r'|' + FRAMEWORK_MARK + r'|/\.mgr/|gl_blob|stratum|--pool|xmr|'
    r'nicehash|nanopool|2miners|/tmp/python|/var/tmp/python|frpc|rev_tunnel|setsid', re.I)
PIPE_SHELL = re.compile(r'(curl|wget|fetch)\b[^\n|]*\|\s*(ba)?sh|base64\s+-d\s*\|', re.I)
UNIT_BAD = re.compile(MINER_NAMES + r'|' + FRAMEWORK_MARK, re.I)
TIMER_FAST = re.compile(r'OnUnitActiveSec\s*=\s*(\d+)\s*(s|sec|seconds)?', re.I)

SEV = {'HIGH': 0, 'MED': 1, 'LOW': 2}
findings = []


def add(check, sev, path, evidence, why, layer=''):
    findings.append({'check': check, 'severity': sev, 'layer': layer,
                     'path': str(path), 'evidence': evidence[:300], 'why': why})


def read_head(p, n=4096):
    try:
        with open(p, 'r', errors='replace') as fh:
            return fh.read(n)
    except Exception:
        return ''


def walk_bounded(base, max_depth, max_entries, budget):
    """按深度/条目上限遍历, 返回 (dirs, files) 的 (Path, depth)."""
    out = []
    base = Path(base)
    if not base.exists():
        return out
    stack = [(base, 0)]
    n = 0
    while stack:
        cur, d = stack.pop()
        try:
            it = list(os.scandir(cur))
        except Exception:
            continue
        for e in it:
            n += 1
            budget[0] -= 1
            if budget[0] <= 0 or n > max_entries:
                return out
            p = Path(e.path)
            out.append((p, d))
            if e.is_dir(follow_symlinks=False) and d < max_depth:
                stack.append((p, d + 1))
    return out


def scan_trees(root, max_depth, max_entries, budget):
    """返回 root 下若干热点子树里所有 (path, depth) 条目。"""
    subs = ['etc', 'root', 'home', 'tmp', 'var/tmp', 'dev/shm', 'var/spool',
            'usr/local/bin', 'usr/local/sbin', 'opt']
    items = []
    for s in subs:
        items += walk_bounded(root / s, max_depth, max_entries, budget)
    return items


# ---------------------------------------------------------------- 层 1/2/3
def check_cron(root, items, cfg):
    """L2/L3: /etc/cron.d 、cron 目录、用户 crontab、/etc/crontab"""
    for p, _d in items:
        name = p.name
        if 'cron' not in str(p).lower():
            continue
        if not p.is_file():
            continue
        # zz 前缀 = 字典序末尾, 逃避人工审查
        if name.startswith('zz'):
            ev = '文件名 zz 前缀(字典序末尾, 规避按名排序的人工审查)\n' + read_head(p, 400)
            add('cron_zz_prefix', 'HIGH', p, ev, '框架用 zz 前缀隐藏持久化文件', 'L2/L3')
        body = read_head(p, 4000)
        if CRON_SUSPECT.search(body):
            add('cron_miner_keyword', 'HIGH', p, body, 'cron 内容含矿池/框架/隧道特征', 'L2/L3')
        elif PIPE_SHELL.search(body):
            add('cron_pipe_shell', 'MED', p, body, 'cron 内容为 curl|sh 型下载执行', 'L2/L3')


def check_systemd(root, max_depth, max_entries, budget):
    """L1: systemd unit/timer —— 真正的复活引擎"""
    for dname in ['etc/systemd/system', 'lib/systemd/system', 'usr/lib/systemd/system']:
        d = root / dname
        if not d.is_dir():
            continue
        for p, _ in walk_bounded(d, 4, max_entries, budget):
            if not p.is_file():
                continue
            body = read_head(p, 6000)
            bad_name = bool(UNIT_BAD.search(p.name))
            bad_body = bool(UNIT_BAD.search(body)) or bool(CRON_SUSPECT.search(body))
            if bad_name or bad_body:
                sev = 'HIGH'
                why = '伪装系统守护(nvpmgr 类)/矿机或框架单元'
                add('systemd_unit_framework', sev, p, body, why, 'L1')
            if p.suffix == '.timer':
                m = TIMER_FAST.search(body)
                if m:
                    sec = int(m.group(1))
                    if m.group(2) is None or m.group(2).lower().startswith('s'):
                        sec = sec if m.group(2) else sec * 60
                    if sec <= 120:
                        add('timer_high_frequency', 'HIGH', p,
                            'OnUnitActiveSec=%ds (<120s 高频复活)' % sec,
                            '高频 timer 是"秒级自愈"引擎, 删 cron 后靠它重建', 'L1')
            # systemd 单元里的 Restart=always 会掩盖文件删除
            if 'Restart=always' in body and (bad_name or bad_body):
                add('systemd_restart_always', 'HIGH', p, 'Restart=always + 可疑 ExecStart',
                    'kill 进程会被 systemd 秒级拉活', 'L1')


def check_framework_files(root, items, cfg):
    """框架三件套 / 伪装目录 / 载荷伪装 / 取证留档"""
    mgr_dirs, trios = set(), {}
    for p, d in items:
        if p.is_dir() and p.name == '.mgr':
            add('mgr_dir', 'HIGH', p,
                '目录名 .mgr, 位于应用数据目录下(伪装 ~/.local/share/<app>/.mgr)',
                '框架主目录: boot.sh + guard.py + antirival.rules 存放处', 'L2/L3')
            mgr_dirs.add(str(p))
        if p.is_file():
            if p.name in ('guard.py', 'antirival.rules', 'boot.sh'):
                trios.setdefault(str(p.parent), set()).add(p.name)
            if p.name.startswith('gl_blob_') and p.suffix == '.dat':
                add('payload_masquerade', 'MED', p,
                    '文件名形如 gl_blob_*.dat(.v3 目录), 伪装 Mesa 着色器缓存',
                    '备份载荷伪装成缓存文件', 'L2/L3')
            if p.name.startswith('evidence_'):
                add('framework_evidence', 'MED', p,
                    'evidence_* 留档文件(框架保存竞争对手入侵产物样本)',
                    '框架自带取证意识, 其文件名/时间戳可反查同一攻击者跨机活动', 'L2/L3')
            if re.fullmatch(r'p[0-9a-f]{4,}', p.parent.name or '') and re.search(MINER_NAMES, p.name, re.I):
                add('miner_in_profiles', 'HIGH', p,
                    'profiles/p<随机hex>/<矿机名> 路径 + 矿机二进制名',
                    '矿机藏在随机化路径下', 'L2/L3')
            if re.search(MINER_NAMES, p.name, re.I) and str(p).find('/proc') < 0:
                add('miner_binary_name', 'HIGH', p, '文件名命中矿机二进制黑名单',
                    'CPU/GPU 矿机落地', 'L2/L3')
    for parent, names in trios.items():
        if {'guard.py', 'antirival.rules'} & names:
            add('framework_trio', 'HIGH', Path(parent) / 'boot.sh',
                '同目录存在: ' + ','.join(sorted(names)),
                '框架三件套(主逻辑/进程层杀毒/竞争者指纹库)', 'L2/L3')


# ---------------------------------------------------------------- 层 4
def check_ssh_keys(root, items, cfg):
    """L4: authorized_keys 键固化(每分钟重写, 只留自己 + 定向删对手)"""
    now = time.time()
    for p, _ in items:
        if p.name != 'authorized_keys' or not p.is_file():
            continue
        try:
            st = p.stat()
        except Exception:
            continue
        body = read_head(p, 8000)
        keys = [l for l in body.splitlines() if l.strip() and not l.strip().startswith('#')]
        age = now - st.st_mtime
        ev = 'key 数=%d, mtime=%.0fs 前 (%s)\n%s' % (
            len(keys), age, time.strftime('%F %T', time.localtime(st.st_mtime)),
            '\n'.join(k[:120] for k in keys[:5]))
        if CRON_SUSPECT.search(body):
            add('authorized_keys_framework', 'HIGH', p, ev,
                'key 内容含框架/矿机特征(自建 key 固化)', 'L4')
        if age < 600:
            # LOW 而非 MED: 刚装自己 key / ansible 批推都会命中, 单独不足以定性;
            # 定性靠同文件内容命中框架特征(authorized_keys_framework, HIGH)
            add('authorized_keys_recent_write', 'LOW', p, ev,
                'authorized_keys 刚被改写(<10min): 疑似定时器每分钟重写/清对手 key(需人工确认)', 'L4')


# ---------------------------------------------------------------- 进程层提示
def check_live_hints(root, cfg):
    """进程/网络层只能在真实主机判(scan 树里看不到), 出提示行"""
    hint = ('进程层(真实主机执行, 本探针不碰):\n'
            '  ps -eo pid,ppid,etime,cmd | grep -E "nvidia-persistenced --pool|xmrig|krig-miner"\n'
            '  nvidia-smi --query-compute-apps=pid,process_name --format=csv   # GPU 真占用\n'
            '  nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits  # >=40 才算"活"\n'
            '  ss -tnp | grep ESTAB | grep -vE ":22|:443"                     # 矿池/隧道外连')
    add('live_process_hint', 'LOW', root, hint, '进程层需在真实主机执行', 'proc')


CHECKS = ['cron_zz_prefix', 'cron_miner_keyword', 'cron_pipe_shell',
          'systemd_unit_framework', 'timer_high_frequency', 'systemd_restart_always',
          'mgr_dir', 'framework_trio', 'payload_masquerade', 'framework_evidence',
          'miner_in_profiles', 'miner_binary_name',
          'authorized_keys_framework', 'authorized_keys_recent_write']


def main():
    ap = argparse.ArgumentParser(description='icc/nvpmgr 挖矿劫持框架布点只读排查')
    ap.add_argument('--root', default='/', help='扫描根(默认 /; mock 靶树传目录)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--out', default='')
    ap.add_argument('--max-depth', type=int, default=5)
    ap.add_argument('--max-entries', type=int, default=20000)
    ap.add_argument('--only', default='', help='只跑某些 check(逗号分隔)')
    cfg = ap.parse_args()

    root = Path(cfg.root).resolve()
    if not root.is_dir():
        print('ERROR: --root 不是目录: %s' % root, file=sys.stderr)
        return 2

    budget = [cfg.max_entries]
    items = scan_trees(root, cfg.max_depth, cfg.max_entries, budget)
    check_cron(root, items, cfg)
    check_systemd(root, cfg.max_depth, cfg.max_entries, budget)
    check_framework_files(root, items, cfg)
    check_ssh_keys(root, items, cfg)
    check_live_hints(root, cfg)

    if cfg.only:
        want = set(x.strip() for x in cfg.only.split(',') if x.strip())
        findings[:] = [f for f in findings if f['check'] in want]

    findings.sort(key=lambda f: SEV.get(f['severity'], 9))
    hits = [f for f in findings if f['check'] != 'live_process_hint']
    strong = [f for f in hits if f['severity'] in ('HIGH', 'MED')]
    result = {
        'root': str(root), 'scanned_entries': cfg.max_entries - budget[0],
        'hits': len(hits), 'hits_strong': len(strong),
        'by_check': {c: sum(1 for f in hits if f['check'] == c) for c in CHECKS
                     if any(f['check'] == c for f in hits)},
        'findings': findings,
        # 只 LOW 命中(如 authorized_keys 刚被改写——装 key 的自动化运维也会命中)不定性,
        # 定性只认 HIGH/MED, 避免把正常运维写成"已被劫持"
        'verdict': ('INFECTED_SUSPECT' if strong else 'CLEAN_NO_ICC_FRAMEWORK_MARK'),
    }
    if cfg.out:
        Path(cfg.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if cfg.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('[icc_triage] root=%s scanned=%d verdict=%s hits=%d(强命中=%d)' % (
            root, result['scanned_entries'], result['verdict'], len(hits), len(strong)))
        for f in findings:
            print('  [%s] %-30s %s\n        %s' % (f['severity'], f['check'], f['path'],
                                                   f['why']))
        if not strong:
            print('  未发现 icc/nvpmgr 类框架布点标记(仍需按 host-ir-check 跑常规后门排查)')
    return 10 if strong else 0


if __name__ == '__main__':
    sys.exit(main())
