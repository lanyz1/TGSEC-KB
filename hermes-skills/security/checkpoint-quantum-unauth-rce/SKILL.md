---
name: checkpoint-quantum-unauth-rce
description: Use when 目标出现 Check Point 管理服务器/Quantum Security Gateway 指纹或要打边界设备管理面. 未授权目录穿越上传 RCE(CVE-2026-93616) + VPN 证书校验 RCE(CVE-2026-85102) 与 IoC 排查.
---

# Check Point 管理面 / 网关未授权 RCE（CVE-2026-93616 / CVE-2026-85102）

两条都在野利用，都是「未授权远程 → 任意代码执行」，但打点位置完全不同。

## A 面：安全管理服务器（CVE-2026-93616）—— 优先

- **面**：TCP/**19009** 上的 Security Management Server / Multi-Domain Security Management / Log Server / SmartEvent
- **洞**：目录穿越 + 文件上传 → 未授权上传并执行任意脚本（CVSS 3.1 **9.8**，CWE-22 + CWE-434）
- **在野**：厂商通告原文——"This vulnerability is exploited in the Wild. Check Point is aware of a handful of customers who have been attacked."
- **受影响**：R82.20（无 Jumbo）；R82.10 JHT ≤44；R82 JHT ≤126；R81.20 JHT ≤166；R81.10 JHT ≤190；R80.x/R81 全 EoS
- **不受影响**：Smart-1 Cloud（已修）、Check Point 防火墙设备本体、Spark Firewall
- **修复**：升 Jumbo Hotfix Take；**LivePatch Take 28/29 不覆盖**
- **临时缓解**：把 19009 收到可信 IP（SmartConsole → Manage & Settings → Permissions & Administrators → Trusted Clients，配合 Security Gateway implied rules）

### IoC（在管理服务器 Expert 模式跑，三选一命中即为可疑）

```bash
grep -nHP "login\(loginRequest.*username='[^']{1001,}'" "$MDS_FWDIR"/log/cpm.elg*
ls -l /var/log/dump/usermode/ | grep -e fwm -e mds      # 与上一条时间吻合 → 潜在利用
grep -E "ERROR.*upgrade\.base\.ReflectionUtils.*Failed to load allResourceFiles map from" "$MDS_FWDIR"/log/cpm.elg*
```

第一条的形态是**超长 username**（>1001 字符）触发栈/解析异常 → 配合 core dump 判利用尝试。

## B 面：Quantum Security Gateway（CVE-2026-85102）

- **面**：VPN 协商（IKE 500/4500、证书面）
- **洞**：证书信任校验不当（**CWE-295**）→ 未授权远程在 Gateway 上执行任意代码（CVSS 3.1 9.8）
- **受影响**：R82.10 JHT ≤43、R82 JHT ≤125 等；修 R82.10 JHT 44+ / R82 JHT 126+
- **打点价值**：网站案降权；企业边界/内网横向清单里记一笔，别在纯 Web 战线上追

## 探测

```bash
# 指纹（本库模板只指纹、不炸）
python tools/1day-kit/od_kit.py run --template-id checkpoint-mgmt-unauth-cve-2026-93616 -u https://<target>:19009
```

模板：`tools/1day-kit/custom-templates/checkpoint-mgmt-unauth-cve-2026-93616.yaml`

## 交接口径

- 拿到管理服务器 = 拿到整个安全策略与网关凭据链，价值远高于普通 Web shell；
  但**只做授权范围内的验证**，别用上传面在客户生产防火墙上留文件。
- 边界设备类的同类在野洞：Zyxel GS1900（CVE-2026-7273，LAN 侧栈溢出）、
  Arista VeloCloud VCO on-prem（CVE-2026-93952）、Linux kernel af_alg（CVE-2025-39964）。
