#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2rayN 节点换血脚本(模板) — 把实测可用的 VLESS+REALITY 节点原地写入 guiNDB.db。

用法:
  python update_nodes.py            # dry-run 只打印计划(默认)
  python update_nodes.py APPLY      # 写入(必须先关闭 v2rayN! 自动备份 guiNDB.db)

要点(v2rayN 7.13.2 实证):
  - ConfigType=5 是 VLESS(SOCKS=4), StreamSecurity='reality', Flow='xtls-rprx-vision'
  - 关键列: Security/Id/Network/StreamSecurity/Sni/Fingerprint/PublicKey/ShortId/Flow
  - 脚本对列名做过滤(缺列自动跳过), 写后重启 v2rayN 验证:
      binConfigs/config.json 出现 "protocol":"vless" + reality, 且
      curl --proxy http://127.0.0.1:10808 https://api.ipify.org 返回新出口 IP
节点参数来源: 实测可用的 vless:// 分享链接(订阅/桌面文件), 逐条填入 NODES。
"""
import sqlite3, shutil, sys, os, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = r'C:\\Users\\Administrator\\Desktop\\新v2包\\v2rayN-windows-64-SelfContained\\guiConfigs'  # ← 按实际路径改
DB = os.path.join(BASE, 'guiNDB.db')
APPLY = 'APPLY' in sys.argv

UUID = '<UUID>'                                        # ← 填配置里的 UUID
SNI = 'download-installer.cdn.mozilla.net'            # ← REALITY SNI
# (IndexId, 备注名, 地址, PublicKey, ShortId)  ← 沿用既有行的 IndexId 即"原地替换"
NODES = [
    ('<IndexId_1>', '二狗·美国', '191.40.0.20', '<pbk_1>', '<sid_1>'),
    ('<IndexId_2>', '二狗·香港', '191.40.0.10', '<pbk_2>', '<sid_2>'),
]

if APPLY:
    rc = os.system('tasklist | findstr /i "v2rayN.exe" >nul 2>&1')
    if rc == 0:
        print('!! v2rayN.exe 仍在运行 — 先关闭再 APPLY'); sys.exit(2)

c = sqlite3.connect(DB)
cols = [r[1] for r in c.execute('PRAGMA table_info(ProfileItem)')]
print('ProfileItem 列:', cols)
if APPLY:
    b = DB + '.bak_%s_agent' % time.strftime('%Y%m%d_%H%M%S')
    shutil.copy2(DB, b)
    print('已备份:', b)

for idx, name, addr, pbk, sid in NODES:
    vals = dict(Remarks=name, Address=addr, Port=443, ConfigType=5, Security='none', Id=UUID,
                Network='tcp', StreamSecurity='reality', Sni=SNI, Fingerprint='chrome',
                PublicKey=pbk, ShortId=sid, Flow='xtls-rprx-vision', SpiderX='', Alpn='',
                AllowInsecure='', MuxEnabled=0)
    kv = {k: v for k, v in vals.items() if k in cols}
    upd = ','.join('%s=?' % k for k in kv)
    c.execute('UPDATE ProfileItem SET %s WHERE IndexId=?' % upd, list(kv.values()) + [idx])
    print('  UPDATE', idx, '->', name)

if APPLY:
    c.commit(); print('== 已写入 ==')
else:
    c.rollback(); print('== (dry-run 未写入) ==')
for r in c.execute('SELECT IndexId,Remarks,Address,Port FROM ProfileItem'):
    print('  ', tuple(r))
c.close()
