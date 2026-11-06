---
name: spa-source-leak-endpoint-mining
description: "Use when SPA 工程根/chunk 泄露需挖后端端点。"
version: 1.0.0
tags: [pentest, web, spa, vite, javascript, api, recon, endpoint]
---

# SPA Source-Leak → Backend Endpoint Mining

从 SPA 的工程根文件与 JS chunk 图恢复后端端点。适用于 Vite / Webpack / Next.js。
重点不是“拿到 JS”，而是：**chunk 图完整展开 → 端点提取 → 契约验证 → 新 IP 镜像判定**。
目录爆破全 404、但前端能正常跑时，这条链通常比继续爆破有效一个量级。

## 何时用

- 目标是 Vue3/React/Next.js SPA，`/api`、`/admin` 目录爆破全 404
- `/package.json`、`/vite.config.js`、`/assets/index-*.js` 任一可访问
- 已拿到 bundle，但只看到路由名，想知道真实后端 `.php` / REST 路径
- 新发现一个 IP 也跑同一套前端，需要判断“新后端”还是“同库镜像”

## 核心循环

### 0. 先定协议与出口

非标准端口先各打一发：

```bash
curl -k -sS -m 8 -o /tmp/h -w 'https %{http_code} %{size_download}\n' "https://HOST:PORT/"
curl    -sS -m 8 -o /tmp/h -w 'http  %{http_code} %{size_download}\n' "http://HOST:PORT/"
```

- HTTP 回 `400`/`000`、HTTPS 回 `200` → **HTTPS-only**，不要写“端口死”。
- 同一主机的 `:80` 301 到 `https://HOST:4455/`，`Location` 直接给出真实 scheme + port。
- 目标有 IP 白名单时走 `--socks5-hostname 127.0.0.1:1080`；直连 403 不代表应用层不存在。

### 1. 工程根裸奔

先查 `/package.json`、`/vite.config.js`、`/vite.config.ts`、`/package-lock.json`：

- `package.json` 能 `json.loads` 且含 `"name"` / `"dependencies"` → 真工程根泄露。
- `vite.config.js` 含 `defineConfig` / `server.proxy` / `target` → 真配置泄露。
- `Content-Type: text/html` + `<!DOCTYPE` → SPA fallback，不是泄露。
- `/src/*` 全 404 **不**能否定工程根泄露；两者是独立静态路径。
- `vite.config.js` 的 proxy target 只是线索，DNS 可能已撤，别当“后端还活着”。

### 2. chunk 图

Vite 的 chunk 文件名在 `__vite__mapDeps` 的 `m.f` 数组里，前缀可能是 `assets/`、`js/`、`./`，不要写死一种：

```js
const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/A-abc.js","assets/B-def.js"])))=>i.map(i=>d[i]);
```

用 `scripts/extract_vite_chunks.py` 扫主入口和所有已下载 JS，输出 `chunks.txt`。
Webpack 看 `static/js/*.js` 与 runtime manifest；Next.js 看 `/_next/static/chunks/`。

### 3. 串行下载

```bash
BASE="https://HOST:PORT"
mkdir -p assets
while read -r n; do
  out="assets/$(basename "$n")"
  [ -s "$out" ] && continue
  curl -k -sS -m 20 --socks5-hostname 127.0.0.1:1080 "$BASE/$n" -o "$out"
done < chunks.txt
```

不要 `xargs -P8`：弱站/代理下常见 `exit -1`、空文件、半包。串行 + `[ -s ] && continue` 断点续传最稳。

### 4. 端点提取

对每个 chunk 抽字符串字面量，再按模式过滤：

- 扁平 PHP：`/[A-Za-z0-9_./-]+\.php(\?[^"'`]*)?`
- REST：`/(api|v\d+|webv\d+|admin|user|pay|withdraw|upload)/...`
- 前端路由：`path:"/..."`、`redirect:"..."`（用于找隐藏后台，不等于 API）

用 `scripts/mine_endpoints.py` 合并去重。

### 5. 验证阶梯

1. 无 token GET → 记录状态/长度/Content-Type。
2. 有 token GET → `200 + 业务 JSON` 才是面。
3. `401` 是闸门、`参数错误` 是契约线索、`405` 是方法不对。
4. 新端点先回对应 route chunk 读字段名，再考虑 POST。
5. `old_pwd/new_pwd/confirm_pwd` = 自助改密，不是 IDOR；不要看到 `change_pwd` 就报越权。
6. 时间盲注只做只读 `SLEEP`，且必须基线 + 多点复测；单次慢响应不算 SQLi。

### 6. 新 IP 镜像判定

同一前端出现在新 IP 时，先比对：

- 同一 token 是否两边都接受；
- 同一 `user.php` / `/me` 是否回同一对象；
- 同一 fatal 错误路径（`/www/wwwroot/.../file.php:line`）是否一致；
- 同一配置 body 长度/hash 是否一致。

全部一致 → **同库镜像**，记为 alias，不重复拖库。不同 IP + 同 token 不是新权限边界。

## Pitfalls

- **`/src/*` 404 ≠ 没有源码**；工程根 `package.json`/`vite.config.js` 可能仍然 200。
- **`package.json` 200 但正文是 HTML** = SPA fallback，不是泄露；必须解析 JSON。
- **Vite chunk 前缀不固定**：`assets/`、`js/`、`./` 都见过；正则只写一种会得到 0 匹配。
- **并发拉 chunk 会假失败**：`xargs -P8` 常见 `exit -1`；串行更稳。
- **路由名 ≠ 后端端点**：`path:"/withdraw"` 是页面路由，真实 API 常在对应 route chunk 里。
- **新端点 ≠ 漏洞**：401/参数错误只说明存在；先补契约再判。
- **403 先读正文**：几百字节含 `ICP`/`备案` = 阿里云备案拦截；`站点创建成功` = 宝塔默认页；`Access denied.` = PHP-FPM 扩展限制。都不是 vhost 或 WAF 绕过问题。
- **FOFA 45012 / crt.sh 429 是限速**，不是“没有资产”；记录错误码，稍后重试或换源。

## Support files

- `references/vite-project-root-and-chunk-mining.md` — 完整命令、正则、82-chunk 案例证据与端点验证结果。
- `scripts/extract_vite_chunks.py` — 从 `__vite__mapDeps` / JS 引号路径抽 chunk 名。
- `scripts/mine_endpoints.py` — 从 chunk 目录抽 PHP/REST 候选端点并去重。

## Related

- SPA 路由/XHR/token 测绘（用户自有技能）→ `spa-api-discovery`、`spa-js-api-mapping`
- 假阳性与镜像控制 → `http-signal-false-positive-triage`
