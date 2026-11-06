# spec 驱动的全量攻击面矩阵（FastAPI 实测）

来源案例：自研「收款记账后台」（FastAPI，nginx → ASGI，裸 IP + Let's Encrypt **纯 IP 证书**
刻意隐藏域名，单机库 `schema_version: 16`）。业务为代收/跑分 + 卡密自动发货 + TG Bot + 收款设备管理。

**结论先行：这是一台加固到位的目标，正面无严重/高危口子。**
本文件的价值有两层：①把「spec 驱动测绘」跑成可复用流程；②给出一份**阴性结果该长什么样**的基线，
避免下次把「我这边没打穿」误报成「目标有洞」。

---

## 1. 起手三发（成本 3 个请求，收益最大）

| 请求 | 实测响应 | 价值 |
|---|---|---|
| `GET /openapi.json` | `200`，**54611 B**，`141 路径 / 151 操作` | 全套接口地图（含路径参数类型） |
| `GET /healthz` | `200`，`{"ok":true,"database":"ok","schema_version":16,"managed_worker_running":true,"disk_free_bytes":124210356224,"service_version":"web-admin-v6-gateway","installation_id":"<24hex>","gateway_configured":true,"callback_worker_enabled":true,"callback_worker_running":true}` | installation_id / 版本 / 磁盘 / **回调 worker 实时开关**（攻击窗口） |
| `GET /health` | `200`，`{"ok":true,"service":"receipt-relay","version":"0.6.2"}` | **第二个服务** ⇒ 判定双服务架构（后台 + 收款网关） |

指纹判定：`{"detail":"Method Not Allowed"}` + `/openapi.json` + `422` 校验体 = FastAPI，三重确认。
`/docs`、`/redoc` 已关（404）而 `/openapi.json` 仍开着 —— **三者是独立开关，各自单独探**。

---

## 2. 全路径 × 全方法矩阵

```python
import json, re, requests
spec = json.load(open("openapi.json"))
s = requests.Session(); s.trust_env = False
s.proxies = {"http": None, "https": None}     # 作业机默认挂 Tor 时必写，否则整批请求被导向死出口
s.verify = False
for p, ops in spec["paths"].items():
    cp = re.sub(r"\{[^}]+\}", "1", p)        # ★ 必须填实，否则整类端点被静默漏掉
    for m in ops:
        r = s.request(m.upper(), BASE + cp, timeout=10, allow_redirects=False,
                      data={} if m in ("post", "put", "patch") else None)
        print(r.status_code, m.upper(), p, r.text[:80])
```

### 四态分桶（自研 FastAPI 后台典型形状）

| 响应 | 含义 |
|---|---|
| `303 → /login` | HTML 页面路由，会话鉴权 |
| `401 {"ok":false,"error":"login_required"}` | 内部 API 路由，会话鉴权 |
| `401 {"ok":false,"error":"invalid_client"}` | 对外 API（商户 pid+key）—— **不同代码路径，必须单独测** |
| `200` / `400` / `415` / `422` | 真·未授权面，逐个深挖 |

本案 151 个操作里，**仅 3 个端点设计性未认证**：

| 端点 | 响应 | 性质 |
|---|---|---|
| `/api.php`、`/submit.php` | `401 invalid_client`（非 form 编码 → `415 form_encoding_required`） | 彩虹易支付兼容面（下单/查单） |
| `/merchant/notify` | `400 {"ok":false,"error":"merchant_callback_pid"}` | **支付回调**，配置未启用 |
| `/pay/{token}` 系列 | `404 order_not_found` | 公开结算页（设计如此） |

**注意 `/reports/data` 返回 `{"error":"unauthorized"}`** —— 与主体 API 的
`{"ok":false,"error":"login_required"}` 不同形，证明是另一套鉴权代码路径，必须单独测。
**形态不同的错误串 = 不同的鉴权实现**，这是分桶时最容易漏的一条。

---

## 3. 免费合约 oracle（别浪费）

| 探针 | 响应 | 推出的结论 |
|---|---|---|
| `POST /merchant/notify` `pid=[a,b]` | `400 duplicate_parameter` | **服务端确实读 `pid` 这个字段名**（且做了重复参数检测） |
| `POST /merchant/notify` JSON body | `415 form_encoding_required` | 只吃 `x-www-form-urlencoded` |
| `GET /merchant/notify` | `400 merchant_callback_pid` | 缺的是**配置值**，不是参数名 |

据此再打 `pid` 值域 **1–1200 + 40 组特殊值**：响应恒定、无 oracle 可枚举
⇒ 结论写成「**配置未启用的死端点**」，而不是「没试出来」。
（同法用在易支付面：22 个候选参数名逐一注入，恒回 `invalid_client` ⇒ 无凭据枚举 oracle。）

---

## 4. 静态资源反推（挖到 JS = 挖到流程）

路由词表 → `<segment>.js` 命中 2 个真实文件：

- **`/static/reports.js`**（2023 B）—— `fetch('/reports/data?' + params)` 直接给出参数名
  `start` / `end`；并逐字段说明响应结构：`data.daily[].date/amount_cents`、`data.platforms[].name`、
  `data.categories[]`、`data.employees[].name/employee_user_id`、`data.business_owners[].name/actor_type`。
  ⇒ **这些参数名 OpenAPI 里一个字都没有，只有 JS 里有。**
- **`/static/collection.js`**（4165 B）—— 暴露核销流程：表单字段
  `verified` / `receipt_id` / `payload_hash` / `source_hash` / `csrf_token`，
  轮询 `data-receipt-poll-url`，`data.version` 变化即整页 reload。

```python
segs = {s for p in spec["paths"] for s in p.strip("/").split("/") if s and not s.startswith("{")}
cands = [f"/static/{n}.js" for n in segs | {n[:-1] for n in segs}]   # 兼试单数形式
```

**字典坑（本次真实踩到）**：首轮目录字典扩展名只带 `.py/.json/.bak/.env/.sql`，
**没带 `.js/.css/.map`**，7552 条全灭并得出「无源码泄露」；补齐后才挖到上述两个文件。

---

## 5. 探针自检铁律（本会话最大教训）

Python 批量扫描器里一行笔误 `proxies={'http': None, 'https': 'none'}`（`'none'` 是**字符串**不是 `None`）
⇒ 每个请求都在客户端抛异常、被 `except: pass` 吞掉 ⇒ 函数返回 `None` ⇒ 判定分支跳过
⇒ 输出「**0 non-404 hits**」，差点当成「nginx 只服务应用本身、无泄露」。

必做两条：

1. `proxies={'http': None, 'https': None}` **且** `session.trust_env = False`
   （shell 侧对应 `unset http_proxy https_proxy ALL_PROXY all_proxy` + `--noproxy '*'`）。
2. **在同一函数体内**先打一条已知 200 的路径并断言：

```python
code, _, _, _ = G("/healthz")
assert code == 200, f"探针自检失败({code}) — 本批结果作废"
```

> 识别信号：**「我明明知道 `/login` 会 200，怎么报 0 命中」** —— 这个自相矛盾就是笔误的暴露点。
> 壳层 curl 自检保护不了 Python 脚本，自检必须走**与批量请求完全相同的那条代码路径**。
> 同源纪律已沉淀在 `recon-negative-validation`（假阴性闸）。

---

## 6. 阴性结果画像：一台「做对了」的 FastAPI 后台

| 攻击面 | 实测结果 |
|---|---|
| 信任代理绕过（`Host: localhost/127.0.0.1`、`XFF`/`X-Real-IP`/`True-Client-IP`/`X-Originating-IP`=`127.0.0.1`、`X-Original-URL`、`X-Rewrite-URL`、`X-Forwarded-Host` 等 20 组） | **全灭**，一律 303/401 |
| 静态目录穿越（`..%2f`、`%252e%252e`、`....//`、`..;/`、反斜杠等 13 种编码） | 全 404/400 |
| 未授权 token 面 SQLi（`'`、`OR '1'='1`、`UNION`、`SLEEP(5)`、`pg_sleep(5)`） | **0.01–0.05s 原速返回** ⇒ 参数化查询 |
| 登录面 XSS（`admin<script>x</script>`） | 无反射（Jinja2 自动转义） |
| 开放重定向（`?next=` / `?redirect=` / `?return=`） | 无此参数，303 固定 → `/login` |
| 请求走私（CL.TE / TE.CL / `TE: xchunked` / `TE :` / 双 TE） | nginx 400/501 全拒 |
| 目录/备份/源码爆破（7552 条，含 `main.py`/`.env`/`.git`/`*.db`/`*.sql`） | **0 命中** |
| 500 / Traceback hunt（超长 path、数组参数、`NaN`/`1e999`、100KB body、Unicode/空字节、畸形 Content-Type/Host） | 无 500、无堆栈 |
| 登录爆破 | **IP 级限流**（`429 尝试次数过多，请稍后再试`），XFF 轮换 5 个值全 429；无用户枚举（响应长度恒等）；时序中位差 2ms |
| 公开 token 端点 | 6590 种形态（自增 1–3000、补零、`p/n/pay/o/ord/order/t` 前缀、hex、日期拼接、4 位全排列）**零命中** ⇒ 强随机（参照本站 CSRF 用 43 字符 `token_urlsafe(32)`，同级熵） |
| FOFA 同族 | `title="收款记账后台"` 精准命中**仅本机** ⇒ 无兄弟站可横向 |
| SSH / TLS | `OpenSSH_9.2p1 Debian-2+deb12u10`（已打补丁）、仅 TLS1.3、ALPN 只有 http/1.1；80 端口全路径 301 → HTTPS |

**这张表本身就是交付物。** 逐条写进报告，把「加固到位」与「我没试」区分开；
用户要的是可复核的阴性证据链，不是「打不穿」三个字。

---

## 7. 本案确认可落报告的信息泄露

| 编号 | 问题 | 级别 |
|---|---|---|
| VULN-01 | `/openapi.json` 未授权暴露 141 路径 / 151 操作（含提权口 `/employees/{user_id}/role`、审计口 `/audit`、资金核销口） | 中 |
| VULN-02 | `/healthz` 泄露 `installation_id` / `schema_version` / 磁盘余量 / 内部 worker 启停 | 低-中 |
| VULN-03 | `/health` 泄露服务名与版本（`receipt-relay 0.6.2`） | 低 |
| VULN-04 | `/merchant/notify` 未认证可达的支付回调（配置未启用），错误串回显内部配置键名 | 低 |
| VULN-05 | `/api.php`、`/submit.php` 未认证易支付面可达 | 低 |
| VULN-06 | `/pay/{token}` 公开面无速率限制（token 强随机，未找到可利用路径） | 低 |
| VULN-07 | HSTS `max-age=86400` 过短；`X-Content-Type-Options: nosniff, nosniff` 重复下发 | 低/信息 |

修复优先级第一项：生产关掉 `openapi_url`
（`FastAPI(openapi_url=None, docs_url=None, redoc_url=None)`）或对其加鉴权。

### 附：Linux 版本横幅的正确读法（防假阳性）

Debian 的 SSH 横幅带补丁级后缀：`OpenSSH_9.2p1 Debian-2+deb12u10`。
**`9.2p1` 落在 regreSSHion（CVE-2024-6387）的上游影响区间内，但 `+deb12u10` ⇒ 早已修复**
（Debian 在 `deb12u2` 就回了这一刀）。
判据：**Debian/Ubuntu 系一律看 `+debNNuM` 后缀，不要拿上游版本号直接套 CVE**，
否则会把已打补丁的主机写进报告当高危。
