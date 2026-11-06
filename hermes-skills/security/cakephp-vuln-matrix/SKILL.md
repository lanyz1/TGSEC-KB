---
name: cakephp-vuln-matrix
description: "Use when 打 CakePHP 应用：7 条 SQLi（含 collate/window）、CRLF、代理信任绕过、缓存反序列化。"
---

# CakePHP 漏洞矩阵（7 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 CakePHP 上一次性产出 7 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `cakephp-attachment-crlf` | High | Remote | CRLF | attachment Content-Type and Content-ID leftover |
| `cakephp-cache-unserialize` | High | Remote | Unserialize | cache engines unserialize objects with no class allowlist |
| `cakephp-collate-sqli` | High | Remote | SQLi | COLLATE collation is a raw SQL fragment |
| `cakephp-cookie-suffix` | High | Remote | Cookie | Http Client cookie jar matches domains as a regex suffix |
| `cakephp-smtp-crlf` | High | Remote | Header injection | SmtpTransport lone LF leftover of GHSA-2qh5 |
| `cakephp-trusted-proxies` | High | Remote | Proxy | trustedProxies honors X-Forwarded-* from any REMOTE_ADDR |
| `cakephp-window-sqli` | High | Remote | SQLi | WindowExpression range/frame offsets spliced into SQL |

## 逐条要点（Class/Reach 原文摘录）
（该产品批次未逐条摘录，直接取 README）

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
