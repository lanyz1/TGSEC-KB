---
name: spa-frontend-recon
description: "Recon SPA sites via SSR payload, JS chunks, API signing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [spa, nuxt, nextjs, vue, ssr, recon, frontend, js-chunk, hmac-signing]
    category: security
---

# 现代 SPA 前端 Recon(SSR payload / JS chunk / API 签名逆向)

针对 Vue3/Vite、Next.js、Nuxt 3 等现代 SPA 站点的前端侦察方法论。SPA 的 API 端点、密钥、签名算法几乎全部以明文/可提取形式存在于前端 JS 中 —— 前端就是最大的信息泄露面。

## When to Use

- 目标是 SPA(页面空白、Vue/React/Nuxt/Next 构建、资源在独立 CDN)
- 直接打 /api/* 返回 403/401,需要找到正确的端点、header 或签名
- 需要从 JS 中提取:API base URL、硬编码密钥、签名机制、内部域名、第三方 token
- 之前抓 HTML 没有有用信息时(SPA 内容全在 JS,不在 HTML)

## Prerequisites

- 目标已授权(用户自有/靶场)
- Python 3(写提取脚本)、curl;必要时 node 用于反查压缩 export


## 全文导航（已拆分）

主卡保留前 2 节；其余 4 节在 `references/full.md`：

- 核心流程
- Pitfalls
- Verification
- References

加载：`skill_view(name='spa-frontend-recon', file_path='references/full.md')`

> 全文较大（26542 字符），已分 2 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
