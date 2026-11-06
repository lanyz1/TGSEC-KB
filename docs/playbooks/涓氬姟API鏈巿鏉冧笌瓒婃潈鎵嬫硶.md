---
title: "业务API未授权与越权手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# 业务API未授权与越权手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/api-param-name-discovery/SKILL.md`
- `/root/.hermes/skills/security/spa-backend-api-pentest/SKILL.md`
- `/root/.hermes/skills/security/unauthenticated-admin-api/SKILL.md`

## 汇总内容

### api-param-name-discovery

来源：`/root/.hermes/skills/security/api-param-name-discovery/SKILL.md`

# API 参数名逆向: 报错驱动爆破 + 前端 chunk 挖参

## 触发场景
- 接口报 `xxx.notBlank` / "Can Not Be Blank" / "Invalid parameter format", 但不知道正确字段名
- 前端表单构造代码在未下载的弹窗/页面 chunk 里, 已有 chunks/ 目录 grep 不到
- 已知端点(从 entry.js 的 API 清单拿到)但参数名反直觉, 瞎猜浪费时间

## 核心技术 1: 报错驱动参数名爆破(核心教训)
服务端对 DTO 的校验错误消息**泄露字段名语义**, 但有两个坑:

1. **主/确认字段都缺失时, 错误消息随机返回**(同一请求两种缺失, 返回哪个看 Map 迭代序)。
 实测: 单发 `{code:X}` → `confirm.notBlank`; 单发 `{newCode:X}` → "Withdrawal Code Can Not Be Blank" — 单发探测结果全是误导, 无法判断主字段是否绑定。
2. **正确姿势(两阶段)**:
 - 阶段A 探确认字段: 逐个候选名单发, 看哪个触发 `confirm` 类错误(说明主字段已绑定、只差确认字段)或先试常见名 `confirm`。
 - 阶段B 固定确认字段, 只换主字段候选名, 每次带两个值:
 - `{"<candidate>": "Test1234", "confirm": "123456"}` → 报 "Password Format Error" / 格式错 = **绑定成功**
 - `{"<candidate>": "Test1234", "confirm": "99999999"}` → 报 "mismatch" = **绑定成功**
 - 报 "Can Not Be Blank" = 没绑上, 换下一个候选
3. 候选词表: `code, newCode, withdrawalCode, newWithdrawalCode, withdrawCode, password, newPassword, verifyCode, authCode, oldCode, confirmCode, <field>Password, <field>Code...` — 命中的往往是最反直觉的那个(如 msg389 提现密码 = `newWithdrawalCode` + `confirm`)。
4. 本库无 Hermes `scripts/param_probe.py`。按本卡候选名用 curl 逐个 POST；授权 API 也可走 `authz-probe`。

## 核心技术 2: 前端 chunk 补抓(已有 chunks/ 不全时)
- Nuxt/Vite 应用: entry.js 路由段直接给出页面→chunk 映射:
 `name:"profile-wallet-add-wallet", path:"/profile/wallet/add-wallet", component:()=>p(()=>import("./chunks/index-index-CHMAGC40.js")...)`
 → 直接 `curl https://<site>/_nuxt/chunks/index-index-CHMAGC40.js` 补抓, 不用整站爬。
- 表单构造代码特征: `new FormData` + `Object.keys(t).map(s=>(s!==void 0&&r.append(s,t[s])))` 的 API 包装 = **multipart 端点**;直接传对象 = JSON 端点。
- **minified 单行 JS 陷阱**: search_files/ripgrep 默认行模式对超长行会 0 命中或截断 → 用 `rg -o '.{0,80}<pattern>.{0,200}' file` 提取上下文;python `re.finditer` 也一样可靠。
- 找 API 方法调用方: 先 grep entry.js 里的方法定义(如 `addWallet(t,n={})`), 再 `rg -o '.{0,100}\.addWallet\(.{0,200}' chunks/*.js` 找调用点拿实参;调用方可能在未下载 chunk, 回到补抓。

## 辅助技巧
- 令牌失效/账号被锁(登录错 15/20 次): 白标博彩一般注册即返回 token, 直接注册新号, 不必过登录滑块。
- 枚举/配置端点(`*-enum/get`, `chain-type/get`, `bank/get{currency}`, `kyc-config/*`)能拿到字段枚举值(int/字符串)、必填项和字段名, 先拉再猜。
- 绑定/设置的"内容字段名"以 `*-user-info/get` 返回的 content dict 为准, 比猜表单快。
- KYC/绑定类端点常是 multipart(含文件字段), 用 `multipart/form-data` 而非 JSON, 否则报 "Missing Servlet Request Parameter" / Type Mismatch。

## 实战记录
- msg389.com(dingyi 白标)提现密码/钱包绑定/KYC 参数全记录: 个案附件未入库（原 references/msg389-wallet-kyc-params.md）

## 交付
- 参数模板 + 每个接口的成功/失败响应贴进战报;证据落 `evidence/<date>-<target>/`。

## 真源

- 手法：`docs/playbooks/业务API未授权与越权手法.md`
- 工具：`python3 tools/ops/api_dispatcher_enum.py --help`

## 2026-10 情报批增量（Dev 常用参数名四表 · @n0aziXss）

- 状态/权限：`debug=true` `test=1` `admin=1` `isAdmin=true` `isPremium=true` `superuser=1` `role=user→admin` `uid=42` `userid=42` `account=42` `profile=42` `ref=partner→internal` `partnerId=1`
- 环境/开关：`stage=dev` `draft=1` `mode=live→test` `settings=default→debug` `config=prod→dev` `preview=true` `env=production→staging` `reportId=999` `documentId=999`
- 缓存/格式：`beta=1` `roleId=1` `rank=1` `step=1` `origin=trusted` `nocache=1` `source=external→internal` `cache=0` `format=json→xml/yaml/php` `output=pdf→json/txt`
- 跳转：`affiliate=evil` `redirect=/dashboard` `redir=/home` `url=evil.com` `next=/secret` `returnUrl=evil.com` `callback=attacker.com` `continue=/admin` `dest=evil.com`
- （2026-02 系列；收口：XSS `inurl:q=|s=|search=`、SQLi `inurl:id=|pid=|category=|action=`）


---

## 外部库增量（2026-10-11 分享包）

## 核心技术 3: 门禁前置型接口的绑定层 oracle(免过门禁探参数)

很多接口在业务逻辑前挂了门禁(图形验证码 / 一次性 token / 未登录校验)。**门禁不改变绑定层的位置**:
Go-Gin `ShouldBindJSON`、Java `@Valid`、NestJS class-validator 都在 handler 之前跑 ⇒
**绑定层错误不用过门禁就能看到**,据此零成本反推字段名/类型/必填。

按出现时机把响应文案分三层(靠文案分类,不靠猜):

| 文案 | 层 | 说明 |
|---|---|---|
| `xxx.notBlank` / 格式错 / `请认真填写` | 绑定层 | 字段名/类型/必填不符 → **未过门禁也能探** |
| `验证码错误` / `token 无效` / 未登录 | 门禁层 | 结构已对、被门禁挡 → 字段名猜对了 |
| `已领取` / `暂未开放` / 业务限制 | 业务层 | **已过墙**,是业务结论 |

判据(同一 client、同一端点连发,别混 UA/会话):
- **字段名**: 候选名逐个换,只有「绑定层报错 ↔ 门禁层报错」的**切换**才算命中(如 `account` 对 / `username` 错)。
- **类型**: 同一字段发 `101`(整型) 与 `"101"`(字符串) → 类型不符会落到绑定层。
- **必填**: 逐个删字段,收集触发绑定错的最小集合。

**假阳性防线**(写报告前必查):
- 空值被「必填」拒 = 绑定层在工作,**不是**空值绕过;只有进业务层才算绕过。
- 门禁文案先取基线: `验证码不存在`/`验证码已失效` 与 `验证码错误` 若可区分,那是 **id 空间 oracle**(可枚举/可预测),不是「字段名对了」。
- 分类器顺序敏感: 同一响应同时含门禁词与格式词时按最具体的一条判,别用「含关键词即命中」的粗暴写法。
  参考实现 + 单测: `tools/ops/ginvue_admin_probe.py::classify_reward_response` · `tests/unit/test_ginvue_captcha_wall.py`。

工具: `python3 tools/ops/ginvue_admin_probe.py captcha-probe --base <URL> --case <案卷>` 自动出 `binder_before_captcha` 判据。

## 核心技术 4: 传输载体必须先定 —— 载体错 = 恒定假阴性(能骗过整轮探测)

字段「读没读到」由**载体**决定,与字段名无关。**任何字段名/存在性探测之前,先

…（截断，全文见来源卡）

### spa-backend-api-pentest

来源：`/root/.hermes/skills/security/spa-backend-api-pentest/SKILL.md`

# SPA + Backend API 渗透方法论（同源壳判别 / 端点挖掘 / BOLA 验证）

适用于：Angular/React/Vue SPA 与后端 API 同域或同 CDN（Cloudflare→CloudFront→S3 / WP 等），常见于交易平台、白标 SaaS、fintech。会话案例见 个案附件未入库（原 references/tradesai-case.md）。

## 1. 同源 SPA 壳判别（找真实 API 路由）

SPA 有 catch-all 路由时，**未路由到后端的路径全部返回 index.html**（200、几十 KB、含 `<!DOCTYPE html>` / `<base href="/">` / `data-critters-container`）。判别法：

- 批量探测路径，按响应体含 `<!DOCTYPE` 或 `<html` 过滤 → 剩下的（空 401 / JSON 400 校验 / JSON 200 / 503）才是真实后端端点
- `/api/health` 返回 **503** 而其余全 200 HTML = 后端存在（路由打到但节点异常）→ 证明 API 在同域后面
- `Accept: application/json` 头不足以绕过壳，按响应体判别才是正解
- 前端 bundle 里出现的 `apiUrl`（如 `https://studio.trades.ai/api/v1`）是 API base 的第一手证据

## 2. Angular main.js 端点挖掘（grep 模板）

下载 `main-*.js` / `scripts-*.js` 后：

```bash
grep -oE '\$\{Zt\.apiUrl\}/[a-zA-Z0-9_/\-\.\$\{]*' main.js | sort -u # 全部 API 路径（template literal）
grep -oE 'this\.[a-zA-Z]+Url=`\$\{Zt\.apiUrl\}/[^`]*`' main.js | sort -u # URL 常量赋值
grep -oE '(get|post|put|delete)\(`?\$\{this\.(baseUrl|apiUrl)\}[^`)]{0,80}' main.js | sort -u
grep -oE '"[a-zA-Z0-9_/]{2,40}"' main.js | sort -u | grep -iE 'hub|wallet|auth|bot|trade|admin|connection'
```

顺序：先找 `{production:!0,apiUrl:"..."}` 配置对象拿 base → 挖子路径（`/Bots/${t}`、`/UserConnections/${t}` 等）→ 对每个端点带 JWT 探测状态码。前端还暴露**路由级敏感面**：`/admin/users`、`/admin/system-stats`、`/admin/financial-report` 等即后台功能清单。

## 3. 客户端 AES "ID 加密" = 纯混淆（别被骗）

JS 里硬编码 key/salt（如 `PBKDF2("TRADESAIHASH_KEY","salt1234",1000,SHA256)` + AES-CBC）对 ID 做"加密"：

- **关键验证：API 是否接受明文 ID**。接受 → 混淆零安全价值（报 Info/Low），顺序 ID 照常枚举
- 不用花时间"破解"它；直接测原始 ID 即可
- 报告里明确：硬编码密钥混淆不是防护，是观感工程

## 4. mail.tm 注册 .NET API 确认邮箱坑

- 确认邮件链接是 fragment：`https://host/confirm_email#token=<b64>&email=<b64>`
- 调 `confirmemail` 时 **`email` 参数传 base64 编码邮箱**（不是解码地址！解码版 500，base64 版 200 返回 accessToken+refreshToken）
- token 含 `+`/`/`，用 requests `params=` 自动编码
- 多封 Confirm Email（同 subject "Confirm Email"）→ 按 `to` 收件地址匹配，别只看 subject

## 5. 双账号 BOLA/IDOR 验证方法论

1. 注册 User A + User B（mail.tm 邮箱，走完确认）
2. 用 A 建测试数据（portfolio/bot/connection），B 的 token 跨账号读 → 干净的水平越权 PoC
3. 无归属校验判定：`GET /UserConnections/{id}` 任意 id 返回 200+凭据 = BOLA 实锤
4. **结构确认法**：枚举时只记录字段名/连接类型/accountName，值脱敏——证明影响范围但不批量落真实数据
5. 顺序 ID 枚举面：JWT `nameid`（用户）、portfolio id、connection id、bot id 全顺序 → 枚举起点即攻击面

## 6. 公开 vs 私有对象判别（防误报）

- `isPublished:true` 的资源对任意登录用户可见 = **市场公开（by design），不是 IDOR**——先对比 `/Marketplace` 类公开端点确认
- 私有对象对非属主返回 500/403 = 该端点有归属校验
- **真正放大器**：公开对象响应泄露内部 ID（bot 详情含 `userConnection.id` + `accountName`）→ 用该 ID 打私有凭据端点。公开→私有 ID 桥接是这类平台最常见的 BOLA 放大链

## 常见防御已验（别重复打）

- `/Portfolios/{id}` 有归属校验（跨账号 404/壳）
- 未发布 bot 500 保护
- JWT alg=none 拒绝 / 弱密钥爆破失败（HS256 正常签名）
- Swagger/OpenAPI 被 SPA 壳吞掉（89KB HTML）→ 不可达即无泄露
- 连接创建时对交易所 API key 做外部校验（假 key → 500）→ 无法用假数据建 Bybit/Binance 连接，改用无需外部校验的类型（TradeLocker/Telegram）或直接测读端点

## 交付

- findings 落地 evidence/；报告 MD（MEDIA 交付）；红队式输出：漏洞 + PoC 步骤 + CVSS + 修复建议
- 敏感数据边界：PoC 用自建账号 + 最小样本，结构确认不批量收割真实用户数据

## 参考

- 个案附件未入库（原 references/tradesai-case.md） — TradesAI 完整案例）（端点表、IDOR 链、AES 混淆细节）

## 真源

- 手法：`docs/playbooks/业务API未授权与越权手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`

---

<!-- 补充视角: spa-api-discovery (兄弟技能库 2026-09-12) -->

---
name: spa-api-discovery
description: "Reveal SPA backend APIs via JS chunks, XHR hooks."
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
    category: security
---

# SPA API Discovery Skill

黑盒渗透 SPA(单页应用)时,不要猜 API 路径——从前端运行时把真实后端接口、请求格式、token 机制挖出来。本技能覆盖 Vue/React 等 SPA 的完整逆向链路:定位 JS → 解压 → 找 API → 抓真实请求 → 复现调用。

## When to Use

- 目标是 Vue3/React SPA,后台 API 路径未知或文档缺失
- curl 复现接口报"参数解析错误/输入值解析错误"等业务错误,怀疑前端对字段做了变换
- 已登录前端但不知道 API 域名/token 头名
- 站点看似有多个 API 域名(迁移/负载均衡),需确认哪个在用

## Prerequisites

- 浏览器工具(browser_navigate / browser_console)
- curl / python(复现请求)

## How to Run

### 1. 定位并下载前端 JS

SPA 的 HTML 里 `<script type="module" src="/static/js/index-XXX.js">` 指向主入口,**主入口往往是加载器,业务代码在 chunk**(HTML 中 `<link rel="modulepreload">` 列出)。

```bash
curl -s --compressed "https://target/static/js/index-XXX.js" -o index.js
# 注意 --compressed!服务器常返回 gzip,不加会得到二进制
zcat file.js > dec.js   # 或 curl -s --compressed 已自动解压
```

### 2. 从 JS 里提取 API 路径与 BASE_URL

```bash
grep -oE '"/api/[^"]{3,80}"' dec.js | sort -u          # 常见绝对路径
grep -oE '(baseURL|BASE_URL)[^,;]{0,80}' dec.js | sort -u  # API 基址
grep -oE 'https?://[a-zA-Z0-9.-]+' dec.js | sort -u    # 全域名(发现迁移/多后端)
```

混淆严重的代码用 `grep -oE '(login|account|password)[^,;]{0,60}'` 找关键字,再回溯上下文。

### 3. 金矿:浏览器 resource timing 看真实请求

在已登录页面的 console 执行——

…（截断，全文见来源卡）

### unauthenticated-admin-api

来源：`/root/.hermes/skills/security/unauthenticated-admin-api/SKILL.md`

# unauthenticated-admin-api（测绘引擎）

目标须在 `config/scope*.json`。本库已有专链时专卡赢。

## 真源

- 长文：`docs/learning/shizhan-pack/skills/redteam/unauthenticated-admin-api/SKILL.md`
- 手法：`docs/playbooks/业务API未授权与越权手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`
- 路由：`python3 tools/ops/shizhan_pack_route.py --name unauthenticated-admin-api`

---

# 管理 API 未鉴权 · OpenAPI 直读手册

> 应对 FastAPI 后台/管理面板（标题含"管理后台"、Vite 单页+FastAPI 栈）。核心：**`/openapi.json` 或 `/api/docs` 把全部管理路由列出来 → 不带 Authorization 直打照样 200 → 等同超管读数据面**。

## 目标判定（先认栈，别撞登录）
- `GET /` 返回 `<title>XX管理后台</title>` + Vite `/assets/index-*.js` → 是管理面板，不是会员站。
- 下一步按 FastAPI 默认探文档，不要扫 WordPress。

## 文档面（未登录）
| URL | 用途 |
|-----|------|
| `GET /openapi.json` | 200 JSON，`info.title` 暴露系统名，全部 path 落表 |
| `GET /api/docs` | Swagger UI |
| `GET /health` | 存活探测 |

## 证明"未鉴权"（关键）
对每条管理 GET（及无破坏的 POST）发请求：
- **不带** Authorization / Cookie
- Host/Origin 用站点自己的即可

对照：若鉴权正常应 401/403；本案全部 **200**。

常见未鉴权管理口（FastAPI 后台族）：
```text
/api/admin/stats
/api/admin/accounts
/api/admin/accounts/{id}/download
/api/admin/bots（含 token 字段）
/api/admin/system-config（api_id/api_hash/路径）
/api/admin/message-config
/api/admin/change-credentials
/api/admin/restart
```

## 每口做什么
- `stats`：先拿数字（total/active/inactive/unauthorized/two_fa_enabled）。
- `bots`：Bot Token 从这里出。只做 getMe 验活，**改 webhook 是破坏面先问**。
- `accounts`：手机号/UID/2FA/状态。`batch-check` 探活可能惊动号；DELETE 毁库存，**默认不要打**。
- `system-config`：api_id/api_hash/session 目录/webhook 基址，按泄露处理。
- `login`：字典未中也要记录（阴性不能结案：读口已把数据吐完）。
- `restart`/delete/change-credentials：**移出默认脚本**，误触会重启服务。

## 前端 JS 陷阱
JS 里若有 `axios.defaults.headers` / `Bearer`，只说明客户端打算带；**服务端没验**。以无头 curl 为准。

## 诚实纪律
- 未鉴权 ≠ 破解了密码；弱口没打中不影响"数据面已拿"。
- 误触 restart 后服务恢复，不要当"已稳定 RCE"。
- Bot Token/api_hash/账号表按已泄露轮换。

## 变体：未鉴权失败 → 弱口令登录 → 配置泄露横向（Wenfxl 实战）
未鉴权口若 401/403，别放弃，转两条路：弱口令 + 文档面继续挖。

### 攻击链（2026-08 Wenfxl Codex Manager 实战验证）
```
1. 扫出 FastAPI 特征（uvicorn + /docs）
2. openapi.json → 101 端点全暴露（含未授权 /api/system/version）
3. 未鉴权口 401 → 试 admin/admin 弱口令登录 → 拿 token
4. 带 token 全量导出：accounts/config/mailboxes
5. config 里翻出 Cloudflare API Key + Clash 代理池 + 邮箱系统 → 横向接管
```

### 弱口令字典（管理面板优先试）
```text
admin/admin  admin/123456  admin/admin888  admin/123  root/root  test/test
```
管理面板（标题"管理后台/Manager/Admin"）优先 admin/admin，命中率最高。

### 配置泄露 → 横向利用清单
拿到 `config.json`/`config_full.json` 后按值翻：
| 字段 | 利用 |
|------|------|
| `cf_api_key` + `cf_api_email` | 验证 Cloudflare 账号 → 域名/Worker/DNS/邮件路由全控 |
| `admin_token`/`admin_auth` | 通用鉴权 token，试在其它口复用 |
| clash 订阅 URL/token | 代理池提取，换出口 IP |
| 批量账号表（email+password） | 上游资源，image2api/CPA 平台复用 |
| 邮箱系统 webhook_secret | 临时邮箱 → 批量注册链路 |
| Worker 源码 | 读取 = 拿到反向代理逻辑，可改可部署 |

### Cloudflare Key 验证（拿下后先验）
```bash
# 用 cf_api_email + cf_api_key 查账号
curl -s "https://api.cloudflare.com/client/v4/accounts" \
  -H "X-Auth-Email: <email>" -H "X-Auth-Key: <key>"
# 列域名
curl -s "https://api.cloudflare.com/client/v4/zones" \
  -H "X-Auth-Email: <email>" -H "X-Auth-Key: <key>" | jq '.result[].name'
# 列 Worker
curl -s "https://api.cloudflare.com/client/v4/accounts/<acct_id>/workers/scripts" \
  -H "Authorization: Bearer <key>"
```
验证通过 = 域名 DNS / Worker / 邮件路由（Catch-all → 临时邮箱）全控，这是重度泄露。

### 教训要点
- openapi.json 列出的口不止数据面，还有 `/restart`、`/change-credentials` 等破坏口，误触会重启/改密，**移出默认脚本**。
- "admin/admin 能登录" 本身是高危项（弱口令），即使数据面没多大价值也是确认漏洞。
- config 里的凭据常是**一套复用到多处**（cf key 同时当 cloudmail admin_password），拿到一个等于一串。
