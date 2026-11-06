# 新葡京娱乐城 (x3891.vip) — 管理后台侦察记录

## 目标
- 前台: `https://3frpf3wtokt7l5bd7booe7v...x3891.vip:9016/`
- CDN DNS: `jkydns806.com`
- IPs: 67.211.68.209, 67.211.70.202, 45.126.181.133, 43.229.5.217
- 系统: Vue 3 + Vite + PHP + OpenResty
- siteId: 100038

## 侦察过程

### 1. 前台访问
HTTPS 端口 9016 返回 OpenResty 402 Payment Required 页：
```
server: openresty
x-cache: BYPASS
```
仅带浏览器 User-Agent 后才返回 SPA HTML（Vue 3 SPA）。

### 2. JS 源码分析
- 前端使用 Vue 3 + Element Plus + Vite + Pinia
- API 通过 `w({Action:"name", Requirement:{...}})` 调用 PHP 后端
- 关键发现: `sitePath` 编码映射，模板域名 `*.siwiueibiviwer.com`
- 关联域名: `abaward.com`, `cbaward888.com/`, `m.dncp-wl99.com/` (硬编码模板)

### 3. 端口扫描
67.211.68.209 上 TCP 开放的端口: 80, 443, 8080, 8443, 8888, 9090, 7001, 8000, 9000, 9016, 10000, 2082, 2083, 3000, 5000, 8088, 8444
但**仅 9016 返回 HTTP 内容** — 其他端口虽 TCP 开放但无 HTTP 响应（负载均衡透传）

### 4. 管理后台路径探测
40+ 常见后台路径全部返回 200 SPA — 管理面板不在此服务器上

### 5. 关联信息
- IP 段 67.211.64.0/20 归属 APNIC (亚太)
- 所有 IP 无 PTR 记录 (反向DNS)
- crt.sh 对 x3891.vip 无收录数据

### 结论
管理后台位于完全不同的服务器/端口上，无法从前台基础设施直接发现。
sitePath 编码（可能是 F106）和模板域名模式可作后续侦察方向。
