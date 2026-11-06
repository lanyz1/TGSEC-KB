#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_scheduled_tasks.py -- 体检本机所有非 Microsoft 计划任务，
列出"哪个会在交互会话里弹出可见控制台窗口"（= 定时闪窗的元凶）。

判定依据（看 PE 头，不看文件名）：
    exe Subsystem == 3 (CONSOLE) 且 LogonType 为 InteractiveToken / 未写
    => 每次触发都分配一个新的可见控制台窗口。
    Subsystem == 2 (GUI)                                  -> 不会弹。
    LogonType = SYSTEM/S4U/ServiceAccount 或只 BootTrigger -> 跑在会话 0，窗口不可见（排除）。

用法（用 python.exe 跑；pythonw 下 stdout 为 None，所以结论同时也写文件）：
    python audit_scheduled_tasks.py
    python audit_scheduled_tasks.py --out D:/tmp/task_audit.txt

只读：不改任何任务、不启停任何进程；调 PowerShell 一律带 CREATE_NO_WINDOW（避免自己污染观测）。
"""
import argparse
import glob
import os
import re
import struct
import subprocess
import sys

CNW = 0x08000000  # CREATE_NO_WINDOW

DUMP_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$dir = Join-Path $env:TEMP 'taskxml_audit'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Get-ChildItem $dir -Filter *.xml | Remove-Item -Force
$i = 0
foreach ($t in (Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '*Microsoft*' })) {
    $i++
    $x = Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath
    if ($x) {
        $n = ('{0:d2}_' -f $i) + ($t.TaskName -replace '[\\/:*?"<>|]', '_')
        $x | Out-File -Encoding Unicode (Join-Path $dir ($n + '.xml'))
    }
}
Write-Output $dir
"""

# 任务里常见的裸 exe 名（由系统 PATH 解析，磁盘上不在工作目录）
BARE = {
    'wscript.exe': 'GUI', 'cscript.exe': 'GUI',
    'cmd.exe': 'CONSOLE', 'cmd': 'CONSOLE',
    'powershell.exe': 'CONSOLE', 'pwsh.exe': 'CONSOLE',
    'python.exe': 'CONSOLE',
}

SAFE_LOGON = ('s4u', 'serviceaccount', 'password', 'system')


def pe_subsystem(path):
    """-> (kind, note)；kind in {GUI, CONSOLE, NATIVE, None}

    ★ 名字不可信：uv 建的 venv 里 \Scripts\pythonw.exe 是 Subsystem=3，照开控制台。
    """
    p = (path or '').strip().strip('"').strip()
    if not p:
        return None, 'empty'
    low = os.path.basename(p).lower()
    if not os.path.isabs(p):
        exp = os.path.expandvars(p)
        if exp != p and os.path.exists(exp):
            p = exp
        elif low in BARE:
            return BARE[low], 'bare-name(%s)' % low
        else:
            return None, 'not-absolute'
    if not os.path.exists(p):
        return None, 'missing'
    try:
        with open(p, 'rb') as f:
            data = f.read(0x800)
        if data[:2] != b'MZ':
            return None, 'not-pe'
        e = struct.unpack_from('<I', data, 0x3C)[0]
        if data[e:e + 4] != b'PE\0\0':
            return None, 'no-pe-sig'
        sub = struct.unpack_from('<H', data, e + 24 + 68)[0]
        return {1: 'NATIVE', 2: 'GUI', 3: 'CONSOLE'}.get(sub, 'sub=%d' % sub), 'ok'
    except Exception as ex:
        return None, 'err:%r' % (ex,)


def dump_tasks():
    r = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-Command', DUMP_PS],
                       capture_output=True, text=True, timeout=180,
                       creationflags=CNW, errors='replace')
    d = (r.stdout or '').strip().splitlines()
    return d[-1].strip() if d else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(os.environ.get('TEMP', '.'), 'task_audit.txt'))
    a = ap.parse_args()

    L = []

    def w(s=''):
        L.append(str(s))

    d = dump_tasks()
    if not d or not os.path.isdir(d):
        w('FAILED to dump scheduled tasks (temp dir not found): %r' % d)
        open(a.out, 'w', encoding='utf-8').write('\n'.join(L))
        return

    rows, risky = [], []
    for f in sorted(glob.glob(os.path.join(d, '*.xml'))):
        src = open(f, 'rb').read().decode('utf-16', errors='replace')
        name = os.path.basename(f)[:-4]
        logon = (re.findall(r'<LogonType>(.*?)</LogonType>', src) or [''])[0]
        trigs = sorted(set(re.findall(r'<(\w+Trigger)>', src)))
        interval = ','.join(re.findall(r'<Interval>([^<]+)</Interval>', src))
        for ex in re.findall(r'<Exec>(.*?)</Exec>', src, re.S):
            m = re.search(r'<Command>(.*?)</Command>', ex, re.S)
            c = m.group(1) if m else ''
            m = re.search(r'<Arguments>(.*?)</Arguments>', ex, re.S)
            args = m.group(1) if m else ''
            kind, note = pe_subsystem(c)
            row = (name, kind or '?', note, logon or '-',
                   ','.join(trigs) + ('[' + interval + ']' if interval else ''), c, args)
            rows.append(row)
            timed = any(t in ('TimeTrigger', 'CalendarTrigger', 'LogonTrigger') for t in trigs)
            if kind == 'CONSOLE' and logon.lower() not in SAFE_LOGON and timed:
                risky.append(row)

    w('%d task XML / %d action' % (len(glob.glob(os.path.join(d, '*.xml'))), len(rows)))
    w('')
    w('%-44s %-9s %-4s %-17s %s' % ('TASK', 'SUBSYS', 'OK', 'LOGONTYPE', 'TRIGGER  |  COMMAND'))
    w('-' * 150)
    for name, kind, note, logon, trig, c, args in rows:
        w('%-44s %-9s %-4s %-17s %s  |  %s %s'
          % (name[:44], kind, note, logon[:17], trig[:30], c[:50], args[:40]))

    w('')
    w('=' * 110)
    w('【会弹控制台窗口的任务】(PE Subsystem=CONSOLE + 交互式身份 + 时间/登录触发)')
    w('=' * 110)
    if not risky:
        w('  无')
    for name, kind, note, logon, trig, c, args in risky:
        w('  任务    : %s' % name)
        w('    命令  : %s %s' % (c, args))
        w('    身份  : %s   触发: %s' % (logon, trig))
    w('')
    w('修法: 入口改 wscript.exe + //B //Nologo "<name>_hidden.vbs"，VBS 内 sh.Run cmd, 0, False（纯 ASCII 外壳）。')
    w('务必先 Export-ScheduledTask 备份原 XML；导入后用 Export-ScheduledTask 回读 Command/Arguments 验证；')
    w('并手动跑一次新外壳确认产物仍在生成（Ready/Result=0 不等于功能正常）。')

    open(a.out, 'w', encoding='utf-8').write('\n'.join(L))
    if sys.stdout is not None:
        sys.stdout.write('report written: %s\n' % a.out)


main()
