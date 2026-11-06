---
name: autonomous-social-engagement
category: social-engineering
priority: P2
score: 6
metadata:
  tags:
    - social-engineering
    - telegram
    - customer-service
    - agent-recruit
    - phishing
    - trust-building
    - osint
    - pretexting
    - autonomous
    - tg-social
    - credential-harvest
    - initial-access
  version: "2.0"
  updated: "2026-09-04"
  author: SurveyEngine
description: >-
  技术面穷尽后的社工/代理推进完整卡。TG 客服/招商社工话术模板、
  代理注册推进流程、客服钓鱼链构造、信息收集到初始访问的完整链。
  Telegram 社工自动盯回复、固定人设、AI 自动回复、状态文件断点续跑。
  触发：继续推进这两条线、自动盯回复、别等我下命令、代理招商社工、
  客服建立信任、autonomous-social-engagement、tg-social-engage。
  无入场券不许空转社工；号库入库/清库仍走 tg-account-library。
globs:
  - "*.session"
  - "*.json"
---

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
身份: 有经验的推广者，手上有流量资源
昵称: 建议用「阿X」「X哥」等本地化昵称
头像: 正常生活照（非明星/网红/默认头像）
个性签名: 简短业务相关（如 "流量合作"）

--- 开场白（首次联系）---
你好，我是做线上推广的，朋友介绍说你们这边在招代理？
想了解一下合作方式和分成比例。

--- 跟进（已读未回 24h 后）---
不好意思打扰了，我手上有不少 [TG群/FB页/抖音] 的流量，
之前在 [竞品名] 做过推广，月均能带 [X] 个有效用户。
方便的话加个微信详聊？或者这边直接说也行。

--- 深入（对方有兴趣）---
好的，那我先注册个代理账号测试一下后台吧。
注册链接发我一下？我先熟悉后台功能，有问题再问你。

--- 获取信息 ---
后台是在哪登录的？我看看网址对不对，别登错了。
结算周期是怎么算的？T+几？
有没有代理后台的使用教程？新手上手可能需要看一下。
```

#### 模板 2: 客服技术咨询（通用场景）

```text
--- 人设 ---
身份: 普通用户 / 潜在客户，遇到技术问题
态度: 礼貌但略焦急

--- 开场白 ---
你好，我在使用你们的 [产品/服务] 时遇到了问题。
[具体问题描述 — 登录失败/充值没到账/功能异常]
能帮我看一下吗？

--- 信息提取 ---
这个问题是不是你们服务器的问题？最近有升级吗？
你们的技术团队在用什么后台系统？我之前用过 [类似产品]，
想确认一下是不是同一个问题。
你们的 APP 是在哪下载的？我重新装一个试试。

--- 升级到技术 ---
我之前做过开发，这个问题看起来像是 [具体猜测]，
你们的技术能看一下日志吗？或者给我看一下报错截图？
```

#### 模板 3: 上游供应商/合作方伪装

```text
--- 人设 ---
身份: 上游支付/技术供应商的对接人
态度: 专业、直接

--- 开场白 ---
你好，我是 [支付公司] 的技术对接人，
我们这边系统升级需要确认一下你们的接口配置。
你是负责技术对接的吗？

--- 信息提取 ---
你们现在用的是哪个版本的 API？
回调地址是不是 [猜测的URL]？
对接人的联系方式发我一下，我直接跟技术沟通。
```

---

## Phase 2: TG 社工执行

### 命令 2-1: 社工代理自动运行

```bash
# 启动社工代理（自动发送/监控/回复）
python3 tools/ops/social_engineer_agent.py run \
  -d <授权域> \
  --goal agent_url \
  --persona "代理招商咨询" \
  --max-rounds 10

# 指定目标 TG 用户
python3 tools/ops/social_engineer_agent.py run \
  -d <授权域> \
  --target @customer_service_bot \
  --goal "获取代理注册链接和后台地址" \
  --persona "有流量的推广者"
```

### 命令 2-2: TG 消息监控与自动回复

```bash
# 监控目标 TG 对话（自动回复模式）
python3 tools/ops/tg_social_monitor.py run \
  --phone <号码> \
  --target @<客服TG> \
  --auto-reply \
  --persona "代理咨询" \
  --log exports/bot-recovery/<案卷>/社工/tg_log.jsonl

# 手动模式（只监控，不自动回复）
python3 tools/ops/tg_social_monitor.py run \
  --phone <号码> \
  --target @<客服TG> \
  --watch-only \
  --log exports/bot-recovery/<案卷>/社工/tg_watch.jsonl
```

### 命令 2-3: TG 消息发送（单条/批量）

```python
#!/usr/bin/env python3
"""TG 消息发送工具（社工推进用）"""
from telethon import TelegramClient
import asyncio, sys, json

SESSION = sys.argv[1]  # .session 文件路径
TARGET = sys.argv[2]   # @username 或 chat_id
MESSAGE = sys.argv[3] if len(sys.argv) > 3 else None

API_ID = 0       # 替换
API_HASH = ""    # 替换

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    # 获取目标实体
    entity = await client.get_entity(TARGET)
    print(f"Target: {entity.first_name or ''} {entity.last_name or ''} (@{entity.username or 'N/A'})")

    if MESSAGE:
        # 发送消息
        msg = await client.send_message(entity, MESSAGE)
        print(f"Sent: {msg.id}")
    else:
        # 读取最近消息
        print("\n=== 最近 10 条消息 ===")
        async for msg in client.iter_messages(entity, limit=10):
            sender = "ME" if msg.out else "THEM"
            print(f"[{msg.date}] {sender}: {msg.text[:200] if msg.text else '<media>'}")

    await client.disconnect()

asyncio.run(main())
```

---

## Phase 3: 代理注册与后台渗透

### 命令 3-1: 代理注册自动化

```python
#!/usr/bin/env python3
"""代理注册自动化（从社工获取的注册链接开始）"""
import requests, re, sys, json, time

REGISTER_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/agent/register"
s = requests.Session()
s.verify = False

# Step 1: 获取注册页面
r = s.get(REGISTER_URL)
print(f"Register page: HTTP {r.status_code}")

# 提取表单字段
fields = re.findall(r'name=["\'](\w+)["\']', r.text)
print(f"Form fields: {fields}")

# 提取 CSRF / hidden fields
hidden = {}
for m in re.finditer(r'<input[^>]+type=["\']hidden["\'][^>]+name=["\'](\w+)["\'][^>]+value=["\']([^"\']*)["\']', r.text):
    hidden[m.group(1)] = m.group(2)
print(f"Hidden fields: {hidden}")

# Step 2: 填写注册（根据实际字段调整）
data = {
    **hidden,
    "username": f"test_agent_{int(time.time()) % 10000}",
    "password": "TestAgent@123",
    "password_confirm": "TestAgent@123",
    "phone": "+8613800138000",
    "email": f"test_{int(time.time()) % 10000}@temp.com",
    "invite_code": "",  # 从社工获取
}

print(f"\nRegistering with: {json.dumps({k:v for k,v in data.items() if 'password' not in k.lower()}, indent=2)}")

# Step 3: 提交注册
r = s.post(REGISTER_URL, data=data, allow_redirects=False)
print(f"Register: HTTP {r.status_code}")
if r.status_code in (301, 302):
    print(f"Redirect: {r.headers.get('Location', 'N/A')}")

# Step 4: 检查是否可以登录
login_urls = ["/agent/login", "/admin/login", "/api/agent/login", "/login"]
for login_url in login_urls:
    base = REGISTER_URL.rsplit('/', 2)[0]
    r = s.get(f"{base}{login_url}")
    if r.status_code == 200 and ('login' in r.text.lower() or 'password' in r.text.lower()):
        print(f"Login page found: {base}{login_url}")
        break
```

### 命令 3-2: 客服对话信息提取

```python
#!/usr/bin/env python3
"""从社工对话日志中自动提取有价值信息"""
import json, re, sys

LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "exports/bot-recovery/<案卷>/社工/tg_log.jsonl"

intel = {
    "urls": set(),
    "emails": set(),
    "phones": set(),
    "usernames": set(),
    "tech_clues": [],
    "credentials": [],
    "key_messages": [],
}

patterns = {
    "urls": r'https?://[^\s<>"]+',
    "emails": r'[\w.+-]+@[\w-]+\.[\w.-]+',
    "phones": r'[\+]?\d{10,13}',
    "tg_users": r'@\w{5,}',
}

try:
    with open(LOG_FILE, 'r') as f:
        for line in f:
            try:
                msg = json.loads(line.strip())
            except:
                continue
            text = msg.get("text", "") or ""

            for name, pat in patterns.items():
                for m in re.finditer(pat, text):
                    intel.get(name, intel.get("urls")).add(m.group())

            # 技术线索
            tech_keywords = ['后台', 'admin', 'login', '密码', 'password', '数据库',
                           'api', 'token', '服务器', 'server', '版本', 'version',
                           '域名', 'domain', '端口', 'port']
            if any(kw in text.lower() for kw in tech_keywords):
                intel["tech_clues"].append(text[:200])

            # 凭据线索
            cred_patterns = [
                r'[用帐账]户?\s*[:：]\s*(\S+)',
                r'密码\s*[:：]\s*(\S+)',
                r'password\s*[:：]\s*(\S+)',
            ]
            for cp in cred_patterns:
                for cm in re.finditer(cp, text, re.I):
                    intel["credentials"].append(cm.group())

except FileNotFoundError:
    print(f"Log file not found: {LOG_FILE}")
    sys.exit(1)

print("=== 社工情报提取 ===")
for key, values in intel.items():
    if values:
        print(f"\n{key}:")
        items = list(values) if isinstance(values, set) else values
        for v in items[:20]:
            print(f"  • {v}")
```

---


## 全文导航（已拆分）

主卡保留前 7 节；其余 7 节在 `references/full.md`：

- Phase 4: 钓鱼链构造
- Phase 5: 完整社工链（信息收集 → 初始访问）
- Phase 6: AI 自动回复引擎
- 已知局限
- 安全红线
- 产出与落盘
- 真源

加载：`skill_view(name='autonomous-social-engagement', file_path='references/full.md')`
