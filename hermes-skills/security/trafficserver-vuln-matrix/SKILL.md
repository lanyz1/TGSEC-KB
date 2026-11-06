---
name: trafficserver-vuln-matrix
description: "Use when 目标前置 Apache Traffic Server (ATS)：9 条 ACL 绕过、SSRF、ESI、RPC 未授权。"
---

# Apache Traffic Server 漏洞矩阵（9 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 Apache Traffic Server 上一次性产出 9 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `ats-authproxy-prefix` | High | Remote | Privilege leftover | authproxy prefix |
| `ats-cripts-rri-uaf` | High | Remote | Crash | Cripts From/To URL UAF |
| `ats-esi-unix-recvport` | High | Remote | SSRF | ESI unix recvport |
| `ats-ipallow-method-case` | High | Remote | Privilege leftover | ip_allow method case |
| `ats-jsonrpc-unrestricted` | High | Local | Privilege leftover | JSON-RPC unix socket unrestricted mode 0777 |
| `ats-magick-unsigned` | High | Remote | File write | unsigned magick convert writes as nobody |
| `ats-realip-plugin-acl` | High | Remote | Privilege leftover | realip PLUGIN ACL fail-open |
| `ats-redirect-zero-net` | High | Remote | SSRF | redirect 0.0.0.0/8 |
| `ats-regex-remap-userinfo` | High | Remote | SSRF | regex_remap noslash $n userinfo origin takeover |

## 逐条要点（Class/Reach 原文摘录）
（该产品批次未逐条摘录，直接取 README）

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
