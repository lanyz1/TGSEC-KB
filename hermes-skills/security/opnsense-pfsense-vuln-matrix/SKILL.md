---
name: opnsense-pfsense-vuln-matrix
description: "Use when 打 OPNsense 或 pfSense 防火墙面板：12 条 uid 提权、锁定绕过、CRLF、固件镜像注入。"
---

# OPNsense / pfSense 漏洞矩阵（12 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 OPNsense / pfSense 上一次性产出 12 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `opnsense-captive-lastseen-roam` | High | Remote | Network-access bypass | captive lastseen roam |
| `opnsense-firmware-mirror-sed` | High | Remote | Privilege leftover | custom firmware mirror sed-skips pkg fingerprints |
| `opnsense-lockout-factory-ip` | High | Remote | Privilege leftover | factory lockout IP |
| `opnsense-ntp-gps-fudge` | High | Remote | Config line injection | NTP GPS fudge |
| `opnsense-tunables-loader` | High | Remote | Config line injection | tunables loader |
| `opnsense-uidfield-system-uid0` | High | Remote | Privilege leftover | UidField uid 0 |
| `opnsense-wlan-wpa-line` | High | Remote | Config line injection | WLAN WPA identity |
| `pfsense-carp-vhid` | High | Remote | RCE | CARP VHID leftover |
| `pfsense-ipsec-login-banner` | High | Remote | RCE | IPsec login_banner start-scripts |
| `pfsense-limiter-number` | High | Remote | RCE | limiter number dnctl |
| `pfsense-openvpn-wizard-crlf` | High | Remote | RCE | OpenVPN wizard CRLF |
| `pfsense-qinq-parent-if` | High | Remote | RCE | QinQ parent-if ifconfig |

## 逐条要点（Class/Reach 原文摘录）
（该产品批次未逐条摘录，直接取 README）

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
