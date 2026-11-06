#!/usr/bin/env python3
"""调得到 ≠ 用得到：扫全库正文，看每张卡里有没有能直接执行的东西。只读。

判据（任一命中即算「有料」）：
  - fenced code block (```)
  - 命令：curl/nmap/python3/sqlmap/nuclei/ffuf/hydra/msfconsole/impacket/hashcat/...
  - payload：<script / ' or '1'='1 / ${jndi: / ../../ / /etc/passwd / {{...}} / UNION SELECT / Runtime.getRuntime

输出：enabled/disabled × {total,no_code,thin,routerish} + 名单，落 /tmp/actionability.json。
口径提醒：零命令的卡很多是「判据/分流卡」（api-sec、engagement-scope-gating、case-review），
设计如此，不是缺陷——报告要拆成「找得到 / 能直接照抄」两档。
"""
import sqlite3, re, json, collections

DB = '/root/.hermes/arsenal/arsenal.db'
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
rows = [dict(r) for r in c.execute(
    "select name,status,body_path,catalog,legacy,description from skills")]

CMD = re.compile(r'(curl\s+-|nmap\s|python3?\s|sqlmap|nuclei|ffuf|hydra|msfconsole|impacket|'
                 r'bloodhound|certipy|chisel|frp|ligolo|hashcat|john\s|gobuster|dirsearch|'
                 r'jwt_tool|ysoserial|mimikatz|proxychains|nc\s+-|bash\s+-i|powershell)', re.I)
PAYLOAD = re.compile(r"(<script|'\s*or\s*'1'='1|\$\{jndi:|\.\./\.\./|/etc/passwd|"
                     r'\{\{.*?\}\}|UNION\s+SELECT|exec\s*\(|Runtime\.getRuntime)', re.I)
ROUTER = re.compile(r'(分流|路由到|见\s*`?references|详见|见另一张|走\s*[a-z-]+\s*卡)')

stat = collections.Counter()
detail = {'no_code': [], 'thin': [], 'router_only': []}
for r in rows:
    try:
        t = open(r['body_path'], encoding='utf-8', errors='replace').read()
    except OSError:
        stat['unreadable'] += 1
        continue
    fences = t.count('```')
    cmds = len(CMD.findall(t))
    pays = len(PAYLOAD.findall(t))
    st = r['status']
    stat[f'{st}_total'] += 1
    if fences == 0 and cmds == 0 and pays == 0:
        stat[f'{st}_no_code'] += 1
        detail['no_code'].append((r['name'], len(t), r['catalog'] or '-'))
    if len(t) < 1200:
        stat[f'{st}_thin'] += 1
        detail['thin'].append((r['name'], len(t)))
    if pays == 0 and cmds < 3 and len(ROUTER.findall(t)) >= 3:
        stat[f'{st}_routerish'] += 1
        detail['router_only'].append((r['name'], len(t)))

print(json.dumps(stat, indent=1, ensure_ascii=False))
print('\nno-code 名单（前 20）:')
for x in detail['no_code'][:20]:
    print('  ', x)
json.dump(detail, open('/tmp/actionability.json', 'w'), ensure_ascii=False)
print('\nfull detail -> /tmp/actionability.json')
