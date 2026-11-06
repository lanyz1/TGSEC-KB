---
name: arsenal-inventory
description: "Use when 老板问「手里多少漏洞/工具」或要盘点本机攻击资产库存。分库清点 + 四层分层汇报。"
version: 1.0.0
tags: [inventory, recon, reporting, cve, arsenal]
---

# 军火库清点与库存汇报

老板问「你现在手里多少个漏洞 / 有多少工具 / 盘点一下家底 / 全部列出来」时的固定动作。

**这是只读盘点，不是一次攻击** —— 不需要目标授权声明，不要把它写成渗透步骤。

## 铁律：数字从磁盘数出来

- **不凭记忆、不引用技能正文的数字。** SKILL.md 正文里的条数是历史批次快照，会过期（某库正文写「76 个产品」时磁盘上已是 121 个目录）。
- 一律跑脚本，一次数完四个池子：

```bash
bash scripts/arsenal_inventory.sh                      # 打印分库账本
bash scripts/arsenal_inventory.sh --json /tmp/a.json   # 落 JSON，便于二次切片
```

## 四个池子（缺一个就是漏报）

- `/root/.hermes/skills/security` — 技能数 / 文件数 / 自建脚本数 / **唯一 CVE 号**
- `/root/TGSEC-Qtzuu/domains/0day-exploits` — 产品目录 / `analysis.md` 条目 / exploit 脚本 / exploitarium / poc-catalog 各子集
- `/root/cve_recon` — NVD 全量归档（含 CVSS 分档）、CISA KEV、Exploit-DB、trickest、统一 PoC 索引、poc_available、product_index、已验真
- `/root/nuclei-templates` — 模板数；再加本机靶场容器与技能内自建脚本

数据底座与检索器（`cve_query.py` / `poc_find.py` / `mine2026.py` / `recon_match.py`）见 `0day-exploit-library` 技能。

## 汇报格式（老板纠过一次，别再犯）

- **问库存 = 要账本，不是要感想。** 按「分库 → 条目 → 小计」全量列出，一行一个数字，总账放最后一行。
- **别开场铺情绒、别只给「一句话回答」。** 被追问「直接列出来全部」就是上一次给少了 —— 数字一次给满。
- **四层必须分开报，不许混：**
  1. **库存** = 情报库条目数（NVD/KEV/Exploit-DB/trickest 并集）
  2. **可打** = 带公网 PoC（`poc_unified` 的 `poc_all` 非空）
  3. **现成武器** = 本地 exploit 脚本 + 技能自建脚本
  4. **已验真** = 靶场亲手打通（见 `0day-exploit-library/references/lab-validated-exploits.md`）

  把 24 万条 CVE 说成「手里的洞」是误导，会被当场拆。
- 可顺手带一句质量备注（外部频道推的「新 CVE」约 1/4 是编的，需 MITRE 验真），但别喧宾夺主。
- 结尾问一句要哪个方向的切片（按产品 / 端口 / CVSS / KEV），并问是否继续开工。
- 清点结论里出现的每个数字都要来自本次脚本输出（或刚跑过的命令），**不复用上次会话的旧数字**。

## 计数坑

- `grep -r` 撞到 `.pyc`/二进制会打 `binary file matches` 污染计数 → 唯一 CVE 计数一律加 `-I`。
- JSON 数组/对象单行落盘时 `wc -l` 只回 **1**，须用 python `len()` 数（`kev.json`/`trickest_index.json`/`product_index.json`/`poc_unified.json` 全是这种）。
- 唯一 CVE 用 `grep -ohE 'CVE-[0-9]{4}-[0-9]{4,7}' | sort -u | wc -l`；`grep -c` 数的是匹配**行**不是唯一号，会把数字虚高数倍。
- 同一技能同时存在于 `skills/security/` 与 `skills/security.bak.*/` 时，裸技能名 `skill_view(name)` 会报 ambiguous → 传分类路径（如 `security/0day-exploit-library`）。目录遍历的清点不受影响。
