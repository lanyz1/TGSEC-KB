---
name: cf-hidden-origin-tracing
description: "Use when tracing real origin behind Cloudflare. CF 后面的站找真实 IP/源站 IP、绕 CF 直连源站。"
tags: [真实IP, 源站IP, 找源站, CF背后, 绕CF, origin, cloudflare]
---

# Tracing an origin hidden behind Cloudflare

For the class of target where DNS and every public index only ever show Cloudflare: the site is
`CF Pages` (or a CF-hosted SPA) plus a **Worker that reverse-proxies `/api/*` to the real origin**.
The origin accepts traffic from the CF network only, so nothing outside it will ever see it.

The job is not "keep scanning" — it is to **collect the leak channels that still exist**, and to
state plainly when the answer is *not externally obtainable* and hand over the in-app path.

## Model the stack before probing

```
DNS  -> CF anycast edge (everything resolves here)        -> no signal
edge -> Worker / Pages Functions (path whitelist, auth)   -> LEAKS the most
     -> origin host (unknown IP, CF-only allowlist)       -> silent by design
```

Signals you can actually harvest: **historical DNS**, **CT logs**, **gateway headers**, **session
cookie contents**, **in-app config endpoints**, and **proof-of-death for candidate IPs**.


## 全文导航（已拆分）

主卡保留前 1 节；其余 4 节在 `references/full.md`：

- Verified techniques (each produced a real finding)
- Reporting discipline (this is what the user actually wants)
- Dead ends — do not spend time here again
- References

加载：`skill_view(name='cf-hidden-origin-tracing', file_path='references/full.md')`

> 全文较大（44559 字符），已分 2 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
