# SPA 硬编码 host → CDN 源站

适用：目标全挂 Cloudflare/类似 CDN，无 MX/SPF，历史 DNS 全是 CDN，FOFA/空间引擎无点，Turnstile 挡自动化——但能让人过验证拿到前端包。

## 流程

1. **让用户过 Turnstile**，Console 跑资产收集（title/url/hosts/assets/apis）；或直接下主包 + Login 分包。
2. **grep 硬编码后端**（不止 API 路径）：
   - `host:"..."` / `Us={...host...}` / `getIp` / `setIp` / `localStorage.getItem("ip")`
   - `httProtocol` / `wsProtocol` / `wss://` / `baseURL` / `getHost`
3. **对硬编码域 + 父域 + 常见标签**（`admin.`/`mail.`/`www.`/`api.`）做 `dig A`。
4. **候选 IP 验证**（共享主机常见：默认证书是别的 CN，**不要**用证书 serial=边沿作唯一准则）：

```bash
# 边沿基线
curl -sk --socks5-hostname 127.0.0.1:9050 --proxy-user t$RANDOM:x \
  https://www.target.com/csapi/serverTime | tee /tmp/edge.json | md5sum

# 源站直连（Tor 绕 Imunify360/类似）
curl -sk --socks5-hostname 127.0.0.1:9050 --proxy-user t$RANDOM:x \
  --resolve www.target.com:443:<CANDIDATE_IP> \
  -H 'Host: www.target.com' -H 'Accept: application/json' \
  https://www.target.com/csapi/serverTime | tee /tmp/origin.json | md5sum
```

决定性：业务 JSON（或 favicon）**与边沿逐字节一致**。

## 实测（opensms.xin）

| 项 | 值 |
|---|---|
| 前端默认 host | `smsb3.1sms.co` |
| 同机族 | `1sms.co` / `admin.1sms.co` / `mail.1sms.co` |
| 源站 IP | **仍未坐实（2026-09 复核，旧结论已撑回）**。`107.180.51.3` = `smsb3.1sms.co`/`1sms.co` 的 GoDaddy **停放机**：4 个 Host（**含真域**）全返同一停放页 ⇒ **判死**；硬编码 host 只是产品**历史默认后端**，不等于现源站 |
| 对撞路径 | `/csapi/serverTime`、`/csapi/checkLogin`、`/favicon.ico` |
| 证书 | 边沿 GTS WE1；源站默认 CN=共享站点（不同 serial 仍可以是源站） |

## 坑

- ip138/类似站点侧边栏「最新 IP」=污染，只信「历史解析记录」表。
- Host=`1sms.co` 可能被 Imunify360 拦；换 `Host:目标 CDN 域` 再打。
- `getHost()` 可能固定返回 `/csapi`（相对路径），真服务器在 `Us.host` / `localStorage.ip`，别只看 API 前缀。
- FOFA `remain_free_point>0` 仍可能 `remain_api_query=0`（820031）——不要空耗，改走用户取包。

## 后续轮次补强（2026-09 实测，非推测）

- **先 dump 响应头：`Location:` 会直接送出「兄弟域 + 第二套应用」。** 对老域名的任意 HTTP 路径取头，实测 `https://www.<old>/...` 回 `location: https://www.<new>/`（301）⇒ 运营方**已换主域**；同法 `nproxy.<old>/...` → 301 → `proxy.<new>` = **另一套独立应用（「管理中控」）**，其 `/api/proxy` 就是**节点/代理下发接口（401）** —— 节点表里常直接是服务器 `IP:port`，是坐实源站最直接的路径。**新主域 = 全新的爆破 / CT / 历史 DNS 靶面**（实测新域 CT 有 23 个节点命名子域、历史解析出过 3 个非 CDN IP）。
- **历史 DNS 命中 ≠ 源站：必须查「同 IP 域名」。** 对历史 A 记录逐 IP 反查共租户：同 IP 挂满无关站（实测全是博彩/彩票站）⇒ **共享高防/CDN 边缘，淘汰**；同日期多 IP（负载均衡/CDN 节点组）尤其要按此筛。只有业务 JSON / favicon 与边沿**逐字节一致**才算源站。
- **「空间引擎零覆盖」本身是结论，不是本轮失败。** 证书 serial/CN、favicon `mmh3`、title、产品特征串全 0 命中 ⇒ 源站只放行 CDN 回源段、对公网隐身；此时**正向路径**（响应头兄弟域 → 新主域历史 DNS + 同 IP 反查 → 中控/节点接口 → 客户端包）优先于继续换字典。
- **认证后横扫与路由爆破要同步做，用来判「有没有 OOB 汇」。** 实测认证后 60+ 端点 + 2600 条路由候选**零 IP 泄露、无收 URL 的参数** ⇒ 带外/SSRF 这条路径直接判死，别把源站溯源的希望全压在它上面。
- **出口被封时先换出口，别改路径；且第三方 CF 前置 API 会连带失败。** 本机 IP 被 CF 1020 拉黑时，异国代理出口实测可 200 拿 SPA + 650KB 主包；同时空间引擎等 CF 前置服务的 API 也会开始回挑战页 —— 别记成「服务挂了」，把该调用也走能过 CF 的出口。challenge 页会**伪装成 `.js` 存下来**，存档前先验 body。详见 `references/waf-fronted-target-recon.md`。
