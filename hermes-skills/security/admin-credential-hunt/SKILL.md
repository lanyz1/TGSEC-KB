---
name: admin-credential-hunt
description: >-
  Admin 后台凭据猎取与登录绕过总卡（不靠大字典）。
  触发：admin不知道密码、后台进不去、管理端口令、默认口令、弱口令打不进、
  凭据在哪里、凭据产地、伪造管理员、免密进后台、登录绕过、路径规范化绕过、403打成200、
  路径穿越鉴权绕过、reset token、密码重置投毒、Host头重置、JWT伪造管理员、
  Session Fixation、2FA绕过、登录SQLi/NoSQLi、空密码登录、未授权管理API、
  兄弟端点鉴权不对称、动词篡改、方法覆盖、catch-all假阳性、锁定策略、
  actuator/env、actuator/httptrace、Druid、heapdump取凭据。
  先判据纪律(基线/差分/锁定)→泄露面→免密绕过→伪造票→接管链→注入→最后才是弱口令。
  专卡：找后台走 admin-console-discovery，未授权API走 unauthenticated-admin-api，
  RBAC走 rbac-bypass-authz，重置走 reset-token-surface，JWT走 jwt-bypass-pentest，
  信任头走 trusted-ip-header，目录泄露走 sensitive-dir-dump，弱口令走 auth-brute。
version: 1.1.0
tags: [j_username, 303]
---

# Admin 凭据猎取与登录绕过（admin-credential-hunt）

**前提**：目标在 `config/scope*.json`。本卡是**总路由**，负责定序与交接，正文不堆 payload。
**一句话**：admin 密码通常在「你还没扫的文件里」，不在「你还在跑的字典里」。

## 何时用

- 拿到管理端 URL / 域名，但账号密码未知
- 弱口令短字典/大字典打不进，想换更高 ROI 的路径
- 要判断「admin 登录能不能直接绕过」
- 有一个普通身份，想进管理面

**不要走本卡**（先专卡）：

| 指纹 | 走 |
|------|-----|
| 管理端域名未知、通配证书 | `admin-console-discovery` |
| 管理 API 整面未鉴权（FastAPI/openapi.json） | `unauthenticated-admin-api` |
| `/actuator`、heapdump、Spring Gateway | `spring-actuator-cloud-takeover`（禁止只扫 health） |
| GVA `authorityId` / 开放注册 | `ginvue-admin-stealth-takeover` |
| 芋道 `/admin-api` + `mock-enable` | `yudao-daifu-mock-file-rce` |
| 纯弱口令/爆破 | `auth-brute` · `docs/playbooks/弱口令与认证爆破手法.md` |
| 只换 uid 读他人 | `object-matrix-authz` |

## 判据纪律（动手前必做，否则假阳性/自伤）

1. **catch-all 基线**：先请求 `/__no_such_<rand>__` 记下状态与长度，**只有不等于基线**的响应才是候选。
   同模板 SPA 对所有未知路径回同一个 `index.html` —— 154 条路径里能误报 **139 条**。
2. **差分判定**：一次只改一个变量。登录成功 = 与「必然失败凭据」基线响应**有差异**，**不是看 200**。
3. **锁定探测**：先提交一次看返回，测出锁定策略（国内后台常见「5 次锁 1 小时/1 天」），别把账号打锁死。
4. **先读再猜**：`robots.txt` / `sitemap.xml` / `api/docs` / `swagger` / `openapi.json` / `README`。
5. **心法**：admin 口令几乎从不「被猜出来」，只被**读出来**或**伪造出来**；大字典是第 8 顺位。
   「打进去」= **控制权**（能调管理 API 改数据 / 拿 shell），不是「页面进去了」。

## 打击顺序（阴性才换下一刀）

```text
⓪ 判据纪律 基线 / 差分 / 锁定 / 先读路由文档
① 泄露面   .env/配置/日志/.git/备份/heapdump/httptrace/Druid/JS bundle → 明文凭据 or SECRET_KEY
② 免密绕过 路径规范化 / 信任IP头 / 未授权管理API / 兄弟端点不对称 / 客户端强制 / 动词篡改 / Host头
③ 伪造票   JWT(alg=none/RS→HS/jwk/kid) / Cookie篡改 / 已知密钥 / Session Fixation
④ 接管链   重置token / Host投毒重置 / OAuth redirect_uri+state / 2FA / 竞态
⑤ 登录注入 SQLi / NoSQLi / 空密码·type混淆 / GraphQL批量
⑥ 弱口令   场景化短字典（最后，且不用大字典）
```

> **族2「兄弟端点鉴权不对称」是 2026 最热在野形态**：同一 handler 两个入口、只有一个挂中间件
> （CVE-2026-33032 MCPwn：`/mcp` 有鉴权、`/mcp_message` 没有，两条请求接管 nginx）。
> 见 `/api/v1/x` 就试 `/api/v2/x` `/api/internal/x` `/api/x` `/api/legacy/x` `/api/admin/x` `/api/x/message`。

## 输入 / 输出

| 项 | 说明 |
|----|------|
| 输入 | `--base https://授权站`；可选 `--case <案卷>`、`--out <json>`、`--max-inject <N>`、`--reset-email <自己的邮箱>` |
| 输出 | JSON 落 `exports/bot-recovery/<案卷>/测绘/admin_access/probe.json` |
| 探针 A | `tools/ops/admin_cred_hunter.py`（凭据来源清道夫：基线法 + 154 路径分 tier + 框架指纹 + JS 挖密 + 锁定保护差分登录） |
| 探针 B | `tools/ops/admin_access_probe.py`（`discover` / `bypass` / `inject` / `reset` / `all`） |
| 靶场 | `tools/ops/_smoke_admin_site.py`（本机回归：`/admin` 默认口令、`/admin2` 锁定、`spa` 兜底假阳性） |
| 真源 | `docs/playbooks/admin凭据获取与登录绕过手法.md` |

## 最短命令

```bash
# ① 先跑清道夫：凭据藏在哪，一次性扫完（凭据面在站点根，入口带路径也能正确推导）
python3 tools/ops/admin_cred_hunter.py -u https://授权站/admin --case <案卷>
# 加登录面小样本探测（带锁定保护 + 差分判定，非爆破）
python3 tools/ops/admin_cred_hunter.py -u https://授权站/admin --case <案卷> \
        --probe-login --login https://授权站/prod-api/login

# ② 再跑登录面/免密/注入/重置
python3 tools/ops/admin_access_probe.py all --base https://授权站 --case <案卷>
python3 tools/ops/admin_access_probe.py discover --base https://授权站 --case <案卷>
python3 tools/ops/admin_access_probe.py inject --base https://授权站 --case <案卷>
python3 tools/ops/admin_access_probe.py reset --base https://授权站 --case <案卷>
```

## 凭据产地 14 类（详解见 references）

**tier1 直接吐凭据**：① 环境/配置 ② Spring Actuator（`env`/`httptrace`/`heapdump`/`loggers`/`jolokia`）
③ Druid 监控台 ④ 日志文件（明文 `login attempt {"user","pass"}`）⑤ 审计日志接口（活 ST/JWT）
⑥ VCS 暴露 ⑦ 备份/归档（`db.sql` → 先判 hash 算法）⑧ 云/运维凭据

**tier2 不吐口令但吐入场券**：⑨ 前端 JS（**appSecret + 签名算法** = 本地复现签名）
⑩ JS 注释里的测试账号 ⑪ 未授权数据面（`resetPasswordToken`）⑫ 未装完的安装向导
⑬ 分享/邀请链接的 localStorage token ⑭ 社会面邮箱（配「找回密码」oracle 确认）

> 四个必记点：**`httptrace` 白送管理员活 token**；**heapdump 是终极杀器但 env 读的密钥不在堆里**；
> **`.env` 的价值是横向+伪造签名，不一定给后台口令**；**`.env` 直读 404 是常态**（靠异常页/日志/备份兜底）。

命中后交接（授权内直接推进，不停在「发现漏洞」）：

```bash
python3 tools/ops/heap_cred_scan.py <文件.hprof> --out exports/bot-recovery/<案卷>/接管/heap_creds/
python3 tools/ops/jwt_forge_probe.py --help
python3 tools/ops/rbac_bypass_probe.py --base https://授权站 --token "$LOW" --case <案卷>
python3 tools/ops/reset_token_surface_probe.py --base https://授权站 --case <案卷>
python3 tools/ops/auth_brute_probe.py -u https://授权站 --case <案卷> --limit 24
python3 tools/ops/object_matrix.py check --case <案卷> --strict
```

## 高频踩坑（Top 6，全表见 Playbook §8.5）

1. **指纹表里一个坏正则整轮崩**：`(fastadmin|?ref=addtabs)` 的 `?` 当量词 → `re.error`。每个 `re.search` 都要 try/except。
2. **入口带路径扫错根**：`-u .../admin` 直接拼 `/.env` 变 `/admin/.env` 全 404。先 `urlsplit` 推 `scheme://host`。
3. **JSON 的 `\uXXXX` 让关键词静默失效**：中文被转义 →「账号已锁定」匹配不到 → 锁定检测报废、拿锁死的账号继续打。**先还义再匹配**。
4. **catch-all 200 是最大假阳性源**（不设基线就满屏命中）。
5. **拿到 hash ≠ 拿到口令**：`$2a$`/`$argon2` 放弃跑字典。
6. **字符集白名单报错 ≠ 登录失败 ≠ 命中**：看到非「密码错误」响应**先分类再下结论**。

## 核心逻辑（探针做什么）

1. **discover**：探 admin/login/console/manage 等路径，记状态、标题、登录标记，分档 `401/403`（有门禁）vs `200`。
2. **bypass**：
   - 对 gated 路径试**路径规范化变体**（`/admin/.`、`/admin/..;/`、`/admin;/`、`/admin%3B/`、`/%2e/admin`、`//admin`、`/Admin`、`/admin%2f`…）→ `401/403 → 200 且像后台` 才算 L2。
   - 试**信任 IP 头**（`X-Forwarded-For` 等 = `127.0.0.1`）。
   - 试**未授权管理 API / 文档面**（`/openapi.json`、`/v3/api-docs`、`/api/admin/*` GET、`/actuator/env`）无票直读。
3. **inject**：登录框少量探测 —— SQLi 报错签名 / NoSQLi JSON / 空密码+type 混淆 / 用户名枚举差异。
4. **reset**：重置面存在性与响应体 token 泄露；`--reset-email` 才触发发信并检查 Host 反射（投毒）。

## 档位（成功口径）

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 管理登录面/文档面清单 + 分档 | 只打开一个登录页 |
| L2 | 免密绕过进管理面；或未授权管理 API 回**他人列表/分页**；或拿到有效管理票 | 401/403；单条 `/me`；匿名也能读（交 authz-probe）；只回显 `admin` 字样；`403→200` 但体是同一块 WAF 挑战页 |
| L3 | 管理写操作 / 配置或 SECRET_KEY 到手 / 跨用户接管（只动自控号） | 只登进去看首页 |

## 失败处理

- 全部阴性 ≠ 结案。**必须回 `测绘/object_matrix.md` 换格子**，禁止写「RBAC/信任头阴性 → 后台进不去」。
- 撞到验证码墙 → `captcha-ocr` / `geetest-captcha-bypass`；撞到锁号/`429` → 立刻停撞，写复工条件。
- 目标有 WAF 拦截 → `python3 tools/evasion-kit/evasion.py`；Java WAF 走 `ghost-bits-cast-attack`。
- 服务 5xx/超时不能默默当阴性；记录并说明目标不可达。

## 红线

- **先问只剩**：改原超管密、删站/清数据、耗余额下单、批量拖号。
- 重置面默认**不提交邮箱发信**；确需触发只用自己注册的邮箱。
- 专卡阴性必须回对象矩阵，禁止直接复工结案。
- 拿到票/密钥后禁止截后台首页结案，必须收配置/密钥/下游凭据。
- 用限流绕过把尝试数从 5 提到 2000 = 实质在跑爆破；须先告知授权边界并保持低频可停。
- `.git*` 是 WAF 高危特征，判定请求放批次最后。

## 支持文件

| 文件 | 内容 |
|------|------|
| `references/credential-source-matrix.md` | 凭据产地 14 类 × 精确路径 × 实测判据 × 拿到后怎么用（154 条） |
| `references/bypass-matrix-path-method-header.md` | 401/403 路径·动词·头全矩阵 + 限流绕过 + nginx 止损点 |
| `references/2026-admin-auth-bypass-cve-map.md` | 2026 在野认证绕过 CVE 速查（CVSS/版本/利用链） |

> 本卡已类级合并 Hermes `admin-cred-and-auth-bypass`（凭据产地 14 类 + 登录绕过 13 族 +
> 判据纪律 + 国产框架专项 + pitfalls）。源头卡不单列，避免同主题碎卡。

## 老 Servlet 后台登录成功判据（2026-10 多目标）
- Struts/老 Java 后台常用 `j_username`/`j_password`（不是 username/password），提交后看 **303 跳转**而不是 200
- 成功特征：303 Location 指向首页/菜单页；失败：200 回登录页并带错误文案
- 前端 `login.do` / `adminLogin.do` / `system/login` 三路径都试；带验证码的先抓 `/captcha.jpg` 看是否固定值
- 弱口令优先：`admin/admin`、`admin/123456`、`system/system`、`manager/manager`

## 默认口令 + 验证码「不校验」（2026-09 taskking 实战）
- `admin/admin123` 直接进，登录页有验证码但**服务端不校验**（随便填/空着都过）
- 判据：验证码填 `0000` 或空 → 仍返回 token
- 配套：未授权 OpenAPI 328 路径、`front/{key}` 配置读取、KYC 证件照直链下载
- 顺序：先试默认口令 + 验证码空过，再谈爆破（省时间且不留爆破日志）
