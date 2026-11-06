# CF 壳后找真机：有效手段与已验证无效清单（2026-09 实证）

针对“域名全在 Cloudflare 后面、DNS 无泄漏”的目标。**先读本文再花时间。**

## ✅ 有效

### 1. urlscan.io 搜索 API（无需 key）——本次唯一命中
```
https://urlscan.io/api/v1/search/?q=domain:<domain>
https://urlscan.io/api/v1/search/?q=page.domain:<domain>
https://urlscan.io/api/v1/search/?q=ip:<ip>          # 反查同 IP 的其他站点
```
返回体含历史解析 IP（`page.ip`）与 `page.server`。本次命中：旧白标子域 → `154.44.24.227`，
`Server: EnevaScdn`，2026-05-01（**非 CF**）。
- 免费层不给 result 详情（要登录），favicon/Server 不完全索引 —— **拿到 IP 就够**。
- 旧 IP 的 web 端口可能已搬走，但 **SSH 还开着**，可据 ASN/地段反推整支服务器集群。
- 同批免费历史库（OTX / threatminer / bufferover / AnubisDB）本次**零新料**（成本低可顺手打）。

### 2. 证书 SAN 扫 —— “这台机器到底服务什么域名”
对每个真实 IP：`openssl s_client -connect <ip>:443 -servername <任意域名>`。
**SNI 被忽略、返回它自己的证书 = 该机器不认这个 vhost；返回的 CN 就是它实际承载的域名。**
本次一次扫出 111 个域名（聊天服务器、节点群、CDN、订阅面板域名）——把裸 IP 变成资产地图的最快手段。

### 3. CF Worker 当出口探针
- 裸 IP `fetch` → `403 error 1003`（Direct IP access not allowed）。
- 绕法：用通配 DNS 域名当 Host：`<ip>.nip.io` / `<ip>.sslip.io`（sslip.io 跑在 OVH，不是 CF）。
- `cloudflare:sockets` 的 `connect()`：**80/443/8080 被 CF 自身拦**（不能当 web 探针），**22/3306 可用**（能做端口存活）。
- 裸 TLS 不支持（`secureTransport:on` 报错让你改用 fetch）→ HTTPS 指纹仍走 `fetch` + nip.io。

## ❌ 已验证无效，别重跑
- **`cf.resolveOverride` 对 CF 托管域名无效**：Worker 子请求带它指向候选 IP 会**回环回 CF 边缘**
  （对照组同样回 CF）。只适用于非 CF 代理的 hostname。
- **前端 bundle 里找源 IP —— 没有**（本次 56 个真 chunk 全拿完）。别把“再挖 chunk”当突破口。
- **CF 前的域名喷密/爆破 —— 死**：锁按用户名全局计（换 IP 无效），且 Turnstile 检查先于锁检查。
- **权威 NS 直查**对 CF 托管记录无 CNAME 泄漏；但历史 A 记录对**未代理**子域仍有效。
  ip138 侧边栏“相关 IP”是广告污染，别当证据。

## “源不在这支舰队”的三条硬指标（同时满足即可停线）
在一台已读穿的机器上：
1. `/proc/net/tcp`+`tcp6` 中**没有 cloudflared 到 CF 边缘（:7844）的活连接**；
2. 目标域名当 Host/SNI 撞它的 80/443 **无对应 vhost/证书**；
3. nginx access.log 的 Host 分布里**没有目标域名**。
→ 结论写“源不在该舰队”，把精力转向真机集群，而不是继续猜 IP。
