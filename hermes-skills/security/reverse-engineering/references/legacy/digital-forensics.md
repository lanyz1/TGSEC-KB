<!-- archived from /root/.hermes/skills/security/digital-forensics/SKILL.md on 2026-10-21 -->

---
name: digital-forensics
description: >-
  数字取证路由卡。触发：Volatility、内存 dump、磁盘镜像、PCAP 取证、
  浏览器/邮件伪证保全。授权 Linux 主机排后门仍走 host-ir-check，不要用本卡替代。
---

> 归档卡：原目录 `/root/.hermes/skills/security/digital-forensics`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/digital-forensics/…')`，不要相对 `references/legacy/` 解析。

# 数字取证（路由卡）

## 本仓探针

```bash
python3 tools/ops/forensic_surface_probe.py drive --path <导出> --case <案>
```

L2=计到凭据类工件；不吐值。证据进案卷 `测绘/`。

```bash
python3 tools/ops/css_query.py list-skills --module 30
python3 tools/ops/css_query.py get --id 30-002
```

| 场景 | 走 |
|------|----|
| 已拿 Linux shell 排后门 | `host-ir-check` · `host_ir_check.py` |
| WP 高熵马 | `wp-shell-drop-hunt` |
| 内存 / 磁盘 / 浏览器取证百科 | CSS 30 |
| 流量还原协议 | `protocol-reverse` |

保全优先于分析：先哈希、只读副本，再开工具。

## 真源

- 手法：`docs/learning/cybersecurity-skills/30-数字取证-DigitalForensics/MODULE.md`
- 工具：`python3 tools/ops/css_query.py list-skills --module 30`

---

<!-- 补充视角: forensics (兄弟技能库 2026-09-12) -->

---
name: forensics
description: Digital forensics — disk image analysis, memory dump, file carving, timeline reconstruction, registry analysis, log parsing, browser history. Trigger: forensics, forensic, analyze disk, memory dump, carve, timeline, evidence.
---

# Forensics

Digital forensics — disk image analysis, memory dump, file carving, timeline reconstruction, registry analysis, log parsing, browser history. Trigger: forensics, forensic, analyze disk, memory dump, carve, timeline, evidence.
