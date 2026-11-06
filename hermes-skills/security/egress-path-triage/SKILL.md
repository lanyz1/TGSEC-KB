---
name: egress-path-triage
description: Use when a probe times out or 200 hides a false positive.
version: 1.0.0
tags: [network, recon, proxy, allowlist, false-positive, vpn]
---

# 出口路径三段判定（代理 / 端口 / 目标 allowlist）

目标打不通时，先别换目标、别换口令、别继续换代理。按三层拆：

```
L1 出口代理是否真的在转发？
L2 代理是否允许该端口出站？
L3 目标是否按来源 IP 白名单拒绝？
```

只有 L1、L2 都证真，L3 的结论才可信。

## 触发条件

- `curl` 返回 `timeout` / `Empty reply` / `code 000`，但 TCP connect 成功。
- 同一目标换多个代理结果互相矛盾。
- FOFA / Shodan / Censys 的 banner 显示服务在，实际 HTTP/TLS 打不通。
- VPN/管理口出现 `Protocol error (code 2)`、TLS ClientHello 后 EOF、握手即断。
- HTTP 200 但 body 是设备页、SPA fallback、登录壳，不是目标内容。

## 1. 先证代理真的在转发

```bash
curl -x "$PROXY" -sS -m 10 https://httpbin.org/ip
curl -x "$PROXY" -sS -m 10 https://api.ipify.org
```

- 返回出口 IP = 真代理。
- TCP connect 成功但 httpbin 失败/空 body = **假通代理**（设备自答、CONNECT 黑洞、只接受不转发），立刻丢弃。
- 不要把「假通代理返回空」记成「目标拒绝」。

## 2. 再证代理允许非标端口

```bash
curl -x "$PROXY" -sS -m 10 http://portquiz.net:992/
curl -x "$PROXY" -sS -m 10 http://portquiz.net:5555/
```

- portquiz 200 = 代理允许该端口出站，问题不在代理端口策略。
- portquiz 也失败 = 代理封非标端口，换出口或改用能出该端口的通道。

## 3. 最后判目标 allowlist

判据（全部满足才下结论）：

1. 多个不同 ASN/地区出口都打目标同一端口；
2. 包含目标所在城市/ISP 的住宅出口；
3. 目标端口全部 timeout / `Empty reply`；
4. 同一代理打 `portquiz.net:<同端口>` 返回 200。

→ **目标按来源 IP 白名单拒绝**。此时继续换代理是负收益；FOFA/Shodan 的 banner 只是历史快照，不能证明当前可达。转向：办公 VPN、CI runner、目标自己的服务器、同运营方已控主机等白名单内立足点；拿不到就收线换面。

国内出口定位：公开列表先批量 `ip-api.com/batch`（100/请求，注意限速）取 `country/regionName/isp/asn`，再挑目标城市/ISP 的节点。机房段命中率极低，别用上万条盲扫。

## 4. 协议层拒绝 ≠ 口令错误

VPN/管理服务在认证前就可能按来源 IP 或协议拒绝：

- SoftEther `vpncmd` 返回 **`Protocol error (code 2)`**：TCP 已通，但服务端在协议/来源层拒绝，**不是密码错**。换 4.43/4.44、换口令都不会过；先确认端口角色和来源白名单。
- 客户端发 TLS ClientHello（`16 03 01`）后服务端立即 EOF：该端口可能不是 TLS VPN 口（SoftEther 992/5555 常是明文 HTML5 控制台），或按来源 IP 拒绝。
- `vpnclient` 4.44 建账户必须带 `/NICNAME`：
  `AccountCreate vpn1 /SERVER:127.0.0.1:992 /HUB:VPN /USERNAME:vpn /NICNAME:VPN`
- 只有进入认证阶段后的「密码错误」才是口令问题；协议错误/EOF 不要写成「口令全失败」。

## 5. HTTP 200 不等于成功

常见假阳性：

- **SPA fallback**：未知路径回 `index.html`，body 是 `<div id="app">` 或固定几百字节 HTML；Vite `/@fs/...` 的 403 也可能是 `server.fs.allow` 白名单拒绝，不是可读。
- **设备自答页**：代理返回 `Server: cl-http`、`AC集中管理平台`、SmartSTB、fnOS、JumpServer、ESXi、RD Web、GlobalProtect 等，实际是设备网页，不是目标。
- **历史 banner**：FOFA/Shodan 的 banner 是扫描器历史快照，不能证明当前可达；必须重新 TCP/HTTP 复核。

判据：看 `Content-Type` + body 特征 + 已知文件标记，不只看状态码。

## 6. 结论模板

```
L1 代理转发：真 / 假（httpbin=...）
L2 端口出站：允许 / 封（portquiz:<port>=...）
L3 目标：可达 / 来源 IP allowlist（多 ASN 全 timeout，portquiz 200）
服务指纹：FOFA banner=...（历史，当前不可达）
下一步：需要白名单内立足点 / 收线换面
```

## Pitfalls

- **TCP connect 成功 ≠ 代理可用**：先 httpbin，再 portquiz，最后才打目标。
- **一个代理失败 ≠ 目标封**：至少换 2-3 个不同 ASN/地区出口，最好包含目标城市/ISP。
- **FOFA banner 是历史**：看到 `HTTP/1.1 202 OK` 不代表现在还能连。
- **`Protocol error` 不是密码错**：不要在协议层拒绝上烧口令配额。
- **200 + SPA fallback 不是文件读/后台**：必须验 body 和 Content-Type。
- **allowlist 结论要写成「不可达的高价值面」**，不要写成「已排除」或「口令全失败」。

## References

- `references/source-ip-allowlist-and-historical-banner.md` — 2026-10 实测案例：SoftEther 办公 VPN 992/5555、假通代理、portquiz 对照、FOFA 历史 banner、Vite SPA fallback 假阳性。
