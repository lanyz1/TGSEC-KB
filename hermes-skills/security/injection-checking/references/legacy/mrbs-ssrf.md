<!-- archived from /root/.hermes/skills/security/mrbs-ssrf/SKILL.md on 2026-10-21 -->

---
name: mrbs-ssrf
description: >-
 授权目标上 Meeting Room Booking System（MRBS）SSRF 作业：CVE-2026-46382。
 用户提到 MRBS、Meeting Room Booking、CVE-2026-46382、会议室预订 SSRF 时使用。
 广谱 1day 走 1day-nuclei-kit；CVE 入库走 cve-daily-intel；云元数据链可并行。
---

> 归档卡：原目录 `/root/.hermes/skills/security/mrbs-ssrf`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/mrbs-ssrf/…')`，不要相对 `references/legacy/` 解析。

# MRBS SSRF / CVE-2026-46382（Cursor Skill）

## 何时用

- 页面标题/路径出现 MRBS、Meeting Room Booking System
- 用户点名 CVE-2026-46382
- `nday_route` hit `mrbs`
- 授权站疑似 PHP 会议室预订系统要排 SSRF

## 真源（按序）

1. `docs/playbooks/MRBS-SSRF手法.md`
2. `tools/1day-kit/custom-templates/mrbs-ssrf-cve-2026-46382.yaml`
3. `docs/playbooks/CVE日报-2026-08-13.md` §2
4. `python3 tools/1day-kit/od_kit.py cvebase lookup --cve CVE-2026-46382 --docs`

## 强制步骤

1. 目标在 scope。
2. 指纹：
 ```bash
 python3 tools/ops/nday_family_probe.py --family mrbs --base https://授权站 --case <案卷>
  ```
3. `cvebase lookup --docs` 钉具体参数/路由后，按 Playbook §2 做 L2： 
 先打**你控制的协作 URL**，再测 scope 内内网/元数据（勿扫无关公网）。
4. 证据：`exports/bot-recovery/<案卷>/测绘/1day/mrbs_ssrf.*` + STATUS。

## 成功口径

| 级别 | 口径 |
|------|------|
| L1 | 确认 MRBS 暴露面 |
| L2 | 协作回调命中 **或** 读到内网/元数据特征响应 |

## 不要做

- 用 SSRF 扫未授权公网段
- 无协作/响应证明就报「可打内网」
- 只扫 CVE 结案

## 衔接

- 打到云元数据/内网密钥 → 按栈切 Actuator/假支付/提权等专链
- 情报入库 → `cve-daily-intel`
- 广谱 → `1day-nuclei-kit`
