#!/usr/bin/env python3
"""Electron 源码地图批量提取(通用版)。
用法: python source_map.py <源码根目录>
输出: 页面→API 映射 / IPC handlers / 分发器 URL / 数据库表 / taskType / WS cmd
"""
import os, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r'D:\渗透\wukong_src'

def read(p):
    try:
        return open(p, encoding='utf-8', errors='ignore').read()
    except:
        return ''

print('=== 1. 页面→API import 映射 ===')
for root, dirs, files in os.walk(os.path.join(ROOT, 'src', 'views')):
    for f in sorted(files):
        if f.endswith('.vue'):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, ROOT).replace('\\', '/')
            c = read(p)
            imports = re.findall(r'import\s+\{?([^}]+)\}?\s+from\s+[\'"]([^\'"]+)[\'"]', c)
            api_imp = [(m.split('/')[-1], n.strip()) for n, m in imports if 'api/' in m or 'request' in m.lower()]
            print(f'{rel} ({c.count(chr(10))}行): {api_imp[:6]}')

print('\n=== 2. IPC handlers(main.ts) ===')
mc = read(os.path.join(ROOT, 'electron', 'main.ts'))
print(re.findall(r"ipcMain\.handle\(['\"]([a-zA-Z0-9]+)['\"]", mc))

print('\n=== 3. 分发器 URL 分支 ===')
for root, dirs, files in os.walk(os.path.join(ROOT, 'electron')):
    for f in files:
        if 'Interceptor' in f and f.endswith('.ts'):
            c = read(os.path.join(root, f))
            branches = re.findall(r'url==\"([a-zA-Z0-9_]+)\"', c)
            if branches:
                print(f'{f}: {len(set(branches))} 个 URL 分支')
                for b in sorted(set(branches))[:40]:
                    print('   ', b)

print('\n=== 4. 数据库表 ===')
for root, dirs, files in os.walk(os.path.join(ROOT, 'electron', 'database')):
    for f in files:
        c = read(os.path.join(root, f))
        tables = set(re.findall(r'CREATE TABLE (?:IF NOT EXISTS )?([a-z_]+(?:\.[a-z_]+)?)', c, re.I))
        if tables:
            print(f'{f}: {len(tables)} 张表')
            for t in sorted(tables):
                print('   ', t)

print('\n=== 5. taskType 枚举(全部前端) ===')
tt = {}
for root, dirs, files in os.walk(os.path.join(ROOT, 'src')):
    for f in files:
        if f.endswith(('.vue', '.ts')):
            c = read(os.path.join(root, f))
            for m in re.finditer(r'taskType\s*[:=]\s*(\d+)', c):
                tt.setdefault(m.group(1), set()).add(os.path.basename(f))
for k in sorted(tt):
    print(f'   taskType={k}: {", ".join(sorted(tt[k]))}')

print('\n=== 6. WS cmd 映射(wss/*.ts) ===')
for root, dirs, files in os.walk(os.path.join(ROOT, 'electron', 'wss')):
    for f in files:
        c = read(os.path.join(root, f))
        lines = c.split('\n')
        cur = None
        for l in lines:
            m = re.match(r'\s*public (?:async |static |override )*([a-zA-Z_$][\w$]*)\s*\(', l)
            if m:
                cur = m.group(1)
            if cur and 'cmd' in l and ('=' in l or 'value' in l):
                cm = re.search(r'cmd\s*[:=]\s*(\d+)|value:"(\d+)"', l)
                if cm:
                    print(f'   {cur} -> cmd {cm.group(1) or cm.group(2)}')
