---
name: virtualbox-vuln-matrix
description: "Use when 有 VirtualBox 7.2.20 本地面：6 条类型混淆/堆溢出/任意读写/文件写。"
---

# VirtualBox 7.2.20 漏洞矩阵（6 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 VirtualBox 7.2.20 上一次性产出 6 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `vbox-guestctrl-copyfrom-dotdot` | High | Local | File write | Guest Control copy-from DOTDOT |
| `vbox-hgcm-ssm-cparms` | High | Local | Heap overflow | HGCM SSM cParms wrap |
| `vbox-lsilogic-sas-config` | Critical | Local | Type confusion / arb R/W | SAS1068 CONFIG SCSI-SPI overlay |
| `vbox-ovf-href-dest-escape` | High | Local | File write | OVF href dest escape |
| `vbox-ovf-nat-tftp-prefix` | High | Local | File read | OVF NAT TFTP empty prefix |
| `vbox-vmdk-sparse-extent` | High | Local | File read | VMDK sparse FLAT extent path join |

## 逐条要点（Class/Reach 原文摘录）
（该产品批次未逐条摘录，直接取 README）

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
