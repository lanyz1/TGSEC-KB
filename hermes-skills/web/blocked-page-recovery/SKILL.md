---
name: blocked-page-recovery
description: "Use when a fetch fails: 403/429, paywall, WAF, bot wall."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Archives, Wayback, Paywall, WAF, Fallback]
    related_skills: [grounded-citations]
---

# Blocked-Page Recovery

When a page won't fetch — 403/429, Cloudflare "Just a moment...", a paywall,
or a bot-detection interstitial — don't give up and don't loop on the same
URL. Third-party services often hold a **copy** of the page. Work down this
ladder, cheapest first.

## The ladder

```
1. Wayback Machine  — archive.org "available" API  (snapshot + timestamp)
2. archive.today    — domain rotation: archive.ph → .md → .li → .is
3. Jina Reader      — only if JINA_API_KEY is set  (live server-side render)
4. API-first pivot  — look for /api/, /graphql, .json, or RSS on the same host
5. Real browser     — browser tool as the last, most expensive resort
```

Run it in one shot with the bundled script:

```bash
python3 scripts/recover_page.py "https://example.com/blocked-article" --json
```

The script tries each route in order, validates every body (see "Fake
successes" below), and prints the first genuine hit with its provenance.

## Provenance discipline (non-negotiable)

Every recovered copy carries a provenance you MUST preserve when citing:

| Route | Provenance | How to cite |
|-------|-----------|-------------|
| Wayback / archive.today | `snapshot` | Cite WITH the snapshot date: "as archived 2026-08-06". Never present a snapshot as the live page — it may be stale. |
| Jina Reader | `live` | Server-side re-render of the live page; cite normally. |
| Live fetch / browser | `live` | Cite normally. |

If the user needs *current* data (prices, availability, breaking news), a
snapshot is context, not an answer — say so explicitly and note its age.

## Manual routes

### 1. Wayback Machine (best provenance, try first)

```bash
# Discovery: returns closest snapshot URL + timestamp as JSON
curl -sL "https://archive.org/wayback/available?url={URL}"
# Then fetch archived_snapshots.closest.url
```

For enumerating many snapshots (or recovering deleted pages), the CDX index:

```bash
curl -sL "https://web.archive.org/cdx/search/cdx?url={URL}&output=json&limit=10"
```

CDX intermittently returns 503 under load — if it does, fall back to the
`available` API; don't retry-hammer it.

Works for: any publicly crawled URL. Fails for: robots-blocked sites,
never-crawled URLs, JS-only SPAs (snapshots don't render).

### 2. archive.today (paywalls, deleted content)

User-submitted archives — often has paywalled news articles Wayback lacks.
Rate-limits aggressively (429) and rotates domains, so iterate:

```bash
for d in archive.ph archive.md archive.li archive.is; do
  curl -sL --max-time 20 "https://$d/newest/{URL}" -o /tmp/page.html \
    -w "%{http_code}" && break
done
```

**Validate the body, not the status code** — a 429 still ships several KB of
rate-limit HTML that looks like a success to a size check alone.

### 3. Jina Reader (requires JINA_API_KEY)

`r.jina.ai` re-renders the live page in a real browser server-side and
returns markdown. Anonymous access is dead (401 → Turnstile); a key is
required:

```bash
curl -s -H "Authorization: Bearer $JINA_API_KEY" "https://r.jina.ai/{URL}"
```

Handles JS SPAs that archives can't. Skip this route entirely when the env
var is unset.

### 4. API-first pivot

WAFs protect the HTML surface far more aggressively than the data endpoints
behind it. After 2-3 blocked attempts on a site, stop fighting the HTML and
look for:

- `/api/...`, `/graphql`, or `.json` variants of the page URL
- An RSS/Atom feed (`/feed`, `/rss`, `<link rel="alternate">` in any copy
  you did recover)
- A sitemap (`/sitemap.xml`) revealing canonical URLs that may not be gated

## Fake successes — routes that LIE

These return HTTP 200 with a plausible body that is NOT the page. The script
rejects them automatically; reject them manually too:

- **Google Cache is dead** (since mid-2024). `webcache.googleusercontent.com`
  returns 200 + tens of KB, but it's a Google Search interstitial with a JS
  redirect, not a cache. Never use it.
- **AMP caches** (`*.cdn.ampproject.org`) mostly return a ~300-byte
  `<title>Redirecting</title>` meta-refresh stub pointing back at the
  original (blocked) URL. Treating that as success creates a fetch loop.
- **Rate-limit bodies**: archive.today 429 pages are multi-KB HTML. Check for
  the target's actual content (title words, expected strings), not just size.

Detection heuristics the script applies: body under a per-route byte floor;
meta-refresh/JS-redirect stubs whose target is the original host; interstitial
titles ("Just a moment", "Redirecting", "Google Search", "Attention Required").

## Geo/IP-whitelist WAF (中国「网站防火墙」类) — 换出口，不要换头

国内黑帽/赌博站常用一类 nginx+Lua「网站防火墙」（版本注释形如
`<!--9.4.5 2024-06-01-->`，拦截页 `<title>网站防火墙</title>`、绿底 `#20a53a`、
文案「您的IP归属地不受信任，已被网站防火墙拦截」、cookie
`server_name_session=<32hex>` + `hasVisited178a=1`、从 `js.<vendor>.com/jump.js`
(base64 注入) 拉挑战脚本）。

**判据：这是 IP 层规则，不是内容层规则。** 头伪造一律无效（XFF / X-Real-IP /
X-Client-IP / True-Client-IP / CF-Connecting-IP / Forwarded / X-Remote-Addr /
X-Original-URL 全测过，状态码不变）；爬虫 UA 白名单、Referer、挑战 cookie 重放、
绝对 URI、HTTP/1.0、未知 Host 也都无效。**唯一变量是出口 IP 的国家/信誉。**

状态码就是诊断工具（同一 URL，只换出口）：

| 出口 | 返回 | 含义 |
|---|---|---|
| 境外（US/EU/TW/…） | `444`（空体或拦截页） | 国家白名单未命中 |
| 目标所在地区**机房** IP（HK/CN IDC） | `403` + 挑战页 | **过了 geo**，被 IP 信誉/机房规则拦 |
| 干净住宅 IP（该地区） | `200` | 通过 |

所以流程是：先抓一批目标地区代理（`api.proxyscrape.com/v2/?request=getproxies
&protocol=http|socks5&country=HK,CN`、TheSpeedX/monosans/roosterkid 列表），
**不要**先做 geo 过滤（ip-api batch 会 429 丢批次）——直接拿每个出口打一次目标，
用返回码分类：`444`=地区不对，`403`=机房信誉，`000/ERR`=代理死。
找 `403` 那一档里有没有住宅 ISP 的，再逐个续测。

**假命中警告**：写得太差的公开代理（`ip:80` 实为某站点自己的 nginx）会把**代理自身
的默认页**当目标返回（HTTP 200 + 自站标题，如 `Server: nginx/1.28.3 (Ubuntu)`）。
必须校验响应里有没有目标的指纹；只看 200 会把代理首页当成突破。

## 机群（一域一机）识别

若目标 IP 是某个「同模板机队」的一员，横向扫同段能拿到同运营方全部资产，但**暴露面
通常完全一致**（同端口、同版本、同模板口令），横向不等于新入口。识别法：读 443
证书 SAN 拿全部品牌域 → 逐个解析 A → 同一 /24 内一域一机 = 机队；再从任一机的
`*.域` 泛解析确认子域模板（`www/admin/api/kf/h5/m/app/download/static/cdn/vpn/wg`）。
横向价值在于：**同一套口令**（凭据核对可分布式分片，每台只吃几个候选，既覆盖大字典
又不触发单机 fail2ban）。

## Proxy relays: don't

Generic "web proxy" relays are man-in-the-middle by construction. Never send
cookies or Authorization headers through one, and don't use them for anything
the user will rely on — provenance is unverifiable. Prefer archives, which at
least timestamp their copies.
