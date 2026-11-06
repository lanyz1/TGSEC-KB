---
name: vpn-attacks
description: "VPN assessment — IKE aggressive mode, weak ciphers, certificate validation bypass, split tunneling abuse. Trigger: vpn, ipsec, ike, openvpn, wireguard."
---

# VPN 边界设备攻击面(SSL VPN 门户 / IKE / 证书解析器)

**核心公式**: **边界设备入口(SSL VPN 门户 / IKE 协商 / 证书解析器) × pre-auth 漏洞形态(解析型内存破坏 / 证书校验缺失 / 认证绕过) × 隧道后利用(进内网 = 边界直穿)**。VPN 是少数"未认证就直达内网"的入口,优先级永远高于普通 Web 资产。

## 1. 攻击面优先级
```
① SSL VPN / 客户端门户(443): 未认证 HTTP 面最大 → 认证绕过 / 路径穿越 / 反序列化 / 证书解析
② IKE(500/4500 UDP): 协商阶段解析型内存破坏(证书/载荷解析器)
③ 管理面(GAiA Web、SmartConsole、各厂管理口): 弱口令 + 已知 CVE,测绘结果里大量暴露
④ 隧道后内网: split tunnel 配置错误 → 客户端即跳板;导出的 .ovpn/L2TP 配置常含明文凭据与内网网段
```
先跑 `scripts/ike_scan.py`(IKE aggressive mode + 供应商/加密套件探针),再 `curl -sk https://<ip>/` 看 Server 头与证书 CN(常直接写产品名);版本对齐厂商 advisory 才能把"疑似"升级成"可报"。

## 2. 实例: Check Point VPN CVE-2026-85102 / CVE-2026-85103(2026-09,NCSC 预警即将在野)
- CVE-2026-85102: VPN 协商期**证书数据校验不当** → 远程在 Security Gateway 上任意代码执行
- CVE-2026-85103: **VPN 证书 ASN.1 解码器堆溢出** → Security Gateway / Security Management Server RCE
- 影响 R81.20 / R82 / R82.10 / R81.10.x / R82.00.x 及 EoS 的 R80–R80.40 / R81 / R81.10;修复 = LivePatch Take 24 或 Jumbo Hotfix(R82.10 T44+ / R82 T126+ / R81.20 T166+);R82.20 不受影响
- **暂无公开 PoC** → 授权测试阶段停在 L1/L2(版本命中 + advisory),别虚报 RCE;客户侧缓解 = Site-to-Site VPN 规则收敛到可信 IP
- 来源: https://www.bleepingcomputer.com/news/security/dutch-ncsc-critical-check-point-vpn-flaws-exploitation-is-imminent/ (详 cve-2026-1day-family)

## 3. 证书校验绕过(scripts/cert_bypass.py)
- 客户端只校验 CN、不校验证书链 → 自签同名证书即可通过(配合自建服务: auth-server-emulation / fake-auth-server-redirect)
- 服务端侧: 若产品把"证书数据校验"放在协商早期且失败不终止连接 → 畸形证书字段就是 fuzz 面(ASN.1 长度/嵌套/负长度)

## 4. Pitfalls
- "听起来能打" ≠ "有洞": 无公开 PoC 时只报版本/advisory 级证据
- 进内网后按 lateral-movement 走,别改客户 VPN 配置(生产);隧道凭据优先从配置文件与客户端内存收割
- 边界设备被植入后重启不掩盖: 内存型(无文件)载荷要按运行时行为取证(参考 F5 BIG-IP "PoisonedRefresh" 内存 webshell 案例)

## 5. 关联
- 相关技能: cve-2026-1day-family、network-pentest、lateral-movement、auth-server-emulation、fake-auth-server-redirect、wireguard-vpn-pivot、proxy-chaining
- 脚本: scripts/ike_scan.py、scripts/cert_bypass.py
