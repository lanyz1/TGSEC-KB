---
name: trusted-ip-header
description: >-
  授权目标上信任 IP 头旁路：X-Forwarded-For / X-Real-IP / True-Client-IP / Client-IP
  把 403 打成 200。HITCON IP 偽造同类。用户提到信任头、IP 伪造、XFF 白名单、
  True-Client-IP 时使用。加款面仍走 hardcoded-token-cfip-fund。
---

# 信任 IP 头旁路

**前提**：目标在 scope。加款 / `CF-Connecting-IP` 走 `hardcoded-token-cfip-fund`。

| 档 | 成立 |
|----|------|
| L1 | `/admin` `/login` `/backend` 基线 401/403 |
| L2 | 伪造环回后变 200，或 302 到 `/admin` `/dashboard`，且体不是同一块 WAF 页 |

```bash
python3 tools/ops/trusted_ip_header_probe.py --base https://授权站 --case <案卷>
python3 tools/ops/ip_whitelist_bypass.py --help
```

## 四刀

1. **钉门** — 先打出会 401/403 的管理路径，没有门禁不要报旁路  
2. **一头一值** — `X-Forwarded-For` `X-Real-IP` `True-Client-IP` `Client-IP` `X-Client-IP` `X-Originating-IP` `Forwarded: for=`，值用 `127.0.0.1` / `::1` / `10.0.0.1`  
3. **链与空白** — `X-Forwarded-For: 1.1.1.1, 127.0.0.1`（有的只信最后一个）；`X-Forwarded-For: 127.0.0.1 ` 带空格  
4. **认源** — 经 CDN 的 200 可能是边缘放行；对照直连源站。命中后填对象矩阵「自己 × 读」

## 失败

基线已是 200 = 没墙，不是洞。状态变了但 body 仍是 CF/WAF 挑战页 = 假阳性。只改 Host 不改 IP 头走 `http-host-header-attacks`。

源站只露 CF、直连要带 Host/XFF 的 **C2 零信任控制台** 走 `c2-zero-trust-console` · `c2_zt_probe.py --origin-ip`，本卡只负责信任头把 403 打成 200。

真源：`docs/playbooks/信任IP头旁路手法.md`

## 未鉴权资金端点 + 伪造内网来源头 + 状态码 oracle（2026-09 AmWager 实战）
- 三个 Affiliate 端点无鉴权，但要求「内网来源」；伪造 `X-Forwarded-For: 10.x/172.16.x` 或 `X-Real-IP` 即过
- **状态码即枚举 oracle**：存在/不存在/被锁返回不同码（200/404/423），无需读响应体
- 配 PIN 爆破：4-6 位纯数字，节流按状态码判定，别按 body
- 判据：伪造头前后状态码差分；用自己的号验证（推荐路径），只做验证不做出金
