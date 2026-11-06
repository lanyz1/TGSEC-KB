---
name: security-encyclopedia
description: "Use when 需要蓝队/取证/合规/检测参考卡（930+ 卡）。"
---

# Security Encyclopedia（英文参考卡仓）

930+ 张英文安全参考卡（Anthropic Cybersecurity Skills 系 + 蓝队/取证/GRC/云安全），**不单独占技能位**，统一走本入口。

## 用法

1. 先读 `references/INDEX.md`（全量清单：卡名 | 字节 | 描述）
2. 按关键词 grep 定位：`grep -i 'kerberoast' references/INDEX.md`
3. 读单卡：`references/<card-name>.md`

## 覆盖域

- 取证/事件响应：analyzing-* / performing-*-forensics / triaging-*
- 检测工程：detecting-* / building-detection-* / configuring-*-logging
- 云安全：auditing-*/ securing-*/ performing-*-cloud-*
- AD/内网：performing-active-directory-* / detecting-*-ticket / conducting-*
- OT/ICS、无线、移动、AI/LLM、供应链、GRC 合规、紫队演练

## 纪律

- 这些是**参考层**，执行时以我方 CJK 实战卡 + domains/ 为准
- 卡内命令需按当前环境改路径/目标，不盲跑
