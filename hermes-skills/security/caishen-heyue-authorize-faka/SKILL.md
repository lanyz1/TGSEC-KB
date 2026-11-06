---
name: caishen-heyue-authorize-faka
description: "Use when 财神杂货铺/heyue/payment-config USDT approve faka."
version: 1.0.0
tags: [caishen, heyue, faka, usdt, approve, dcat, luna, payment-config]
---

# 财神杂货铺 + heyue 授权发卡壳

Laravel/Dcat「财神系统」+ Luna 前台 + TRON **heyue** 合约抽币。硬资产是 spender/owner 控制权与链上 allowance，不是 Destoon 库存卡密。

Related: `defi-authorize-drain`（ops 归集铁律）· `pentest-execution` USDT scam ref。  
Detail casebook: `references/playbook.md`.

## Triggers

- 标题「财神杂货铺」/ 后台「财神系统 - 后台控制中心」
- `GET /payment-config` JSON 含 `permission_address` + `authorized_amount`
- `/assets/luna/` + `idjs.js` + 混淆 `pay.js` + Dcat `v2.0.24-beta`
- 代理 `?id=trc|erc|bsc|okc|pol|grc`+数字
- 合约名 heyue / method `controlAndTransferToken` (`b82a91eb`)

## Critical rules

1. **payment-config 无鉴权 = crown** — 先抓 spender/payment/EVM/model/token
2. 支付是 **approve** 不是 transfer；bill 写 Epusdt 常是壳文案
3. Spender 多为 **heyue 合约**；杀鱼 = owner 调 `controlAndTransferToken` → 要 **owner 钥**（jhlicai 上 payment EOA 即 caller）
4. 无钥 → `BLOCKED_NO_KEY`；只读扫 drainable；归集令才写链
5. 站点 80/443 挂了 → reverse-IP 兄弟域 + 同指纹活站 + **链上 Approval 不停**
6. jhlicai：`/custom-payment` **可无 token**；`create-order` 常 **不强制极验**
7. MySQL open ≠ 可连：`Host not allowed` 白名单
8. 回调 vpay/yipay/epusdt 乱签多返回 `fail` — 别空耗

## Attack order

1. payment-config → loot addresses  
2. custom-payment / create-order → bill + pay.js strings  
3. TronGrid Approvals on spender + decode `b82a91eb` drains  
4. drainable = min(bal, allowance)  
5. admin 字典 / dcat 上传仅登录后  
6. 同 title / payment-config 扩 IP  

## On-chain notes

- Allowance ABI：Base58Check → 去 checksum → 去 `41` → 32B pad（pad 错全 0）
- 出金例：collect → hub `TQpBRa…` → 大罐 `TKEMiZ…`（余额与可抽分栏）
- 外部构造：`tronweb.net/api/approve`（需合法 permission）

## Cases (2026-09)

| Host | IP | Notes |
|------|-----|--------|
| w5v0.shangchengcnc003.icu | 112.213.120.224 | Web later DOWN；spender TJZY3hg…；~490U 历史抽；drainable~7.37U |
| jhlicai.com | 154.12.80.22 | LIVE；payment TMQ839…；~47U 抽；payment≈34U |

Artifacts: `/tmp/w5v0_pentest/` · `/tmp/jhlicai/`
