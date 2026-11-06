# 来源 IP allowlist 与历史 banner 假阳性（2026-10 实测）

## 案例 A：SoftEther 办公 VPN `ckg-ct-office.saturney.io`

- FOFA 证书反查 `cert="qevorixa.org"` / `domain="saturney.io"` 拉出该子域；A 记录历史 `125.85.59.206`、`14.110.111.200`，当前 `14.110.110.61`。
- 端口 **992 / 5555**。FOFA banner：`HTTP/1.1 202 OK`、`Content-Type: text/html`、1999 字节 → SoftEther HTML5 控制台，不是普通 nginx。
- 本地 nmap 直接打三台：全 filtered（本机出口被目标拒绝）。
- 国内代理池 644 条 → 地理定位出 9 条重庆出口；`113.249.111.67:1080`（重庆电信 AS134420）为真代理，`portquiz.net:992/5555` 均 200，证明代理允许非标端口。
- 同一代理打三台目标 IP 的 80/443/992/5555：全部 `ConnectionError` / timeout / `Empty reply`。
- `vpncmd` 4.43 与 4.44 经中继 TCP connect 成功，空口令/常见口令统一 **`Protocol error (code 2)`**；`vpnclient` 建号 `vpn1`（HUB `VPN`，USER `vpn`）后状态 `Retrying`；992 首包 TLS ClientHello `16 03 01` 后服务端 EOF；明文 HTTP 打 992/5555 也 `Empty reply`。
- **结论：目标按来源 IP 白名单拒绝，FOFA banner 是历史快照。** 不是口令错，不是代理封端口，不是服务下线。继续换代理负收益。

## 案例 B：假通代理

- `175.27.252.26:1080`：TCP connect 成功，但对 `httpbin.org` 失败、对目标也不转发 → 假通代理。
- 判据：先 `curl -x <proxy> https://httpbin.org/ip`，失败即丢弃；不要用它得出的「目标不可达」结论。

## 案例 C：Vite `/@fs` 的 403 与 SPA fallback

- `hub.saturney.cn`（Vite dev server）：`/@fs/etc/passwd` → **403**（`server.fs.allow` 拒绝）；`/@fs/app/.env?raw` → **200** 但 359 字节 HTML SPA fallback，不是文件内容。
- `/@fs` 全 403 时不要继续换编码；转根路径静态 `/.env`、`/package.json?raw`，并用 `Content-Type` + body 特征确认。

## 操作要点

1. 代理真实性（httpbin）→ 端口出站（portquiz）→ 目标 allowlist（多 ASN + 目标城市住宅出口）三段依次证。
2. 只有 portquiz 200 且目标端口全 timeout，才写 allowlist；否则先怀疑代理/端口。
3. FOFA/Shodan banner 只能当指纹，必须重新 TCP/HTTP 复核当前可达性。
4. 协议层拒绝（`Protocol error`、TLS EOF）不算口令失败，不要烧口令配额。
5. allowlist 的下一步是找白名单内立足点，不是继续换代理。
