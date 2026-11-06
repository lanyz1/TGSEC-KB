---
name: safe-bulk-cleanup
description: Use when purging unused files, freeing disk space, or shrinking a bloated git repo.
---

# Safe Bulk Cleanup — housekeeping / campaign decommissioning

Triggers:「清理掉所有没有用的」「能删除的 用不到的都删除」「停止所有任务」「先清理磁盘」「换新目标」, disk-full panics, retiring old target workspaces after a campaign.

Goal: maximum space reclaimed, ZERO collateral damage. A wrong `rm` can kill live ops, another agent's work, or the only copy of campaign loot — and it is irreversible.

## Iron rules
1. **Provenance before deleting shared/unknown dirs.** Fresh mtime (written today) = least likely to be "unused". Identify who created it and whether anything still references/uses it first.
2. **Archive before delete.** Copy small high-value files (reports, creds, notes, cookies, small scripts — ≤256K, non-binary) into an archive dir. Bulk (captchas, dumps, logs, node_modules) doesn't need archiving.
3. **Two-phase execution, never one-shot.** Phase A = archive-only; spot-verify key files exist; Phase B = delete behind an assertion gate.
4. **Manifest everything** → `deep-cleanup-manifest-<date>.md` (paths, sizes, freed total, errors). Doubles as the user's receipt.
5. **Verify after:** `df -h /` before/after; services still alive; cleared dirs gone; keep-list intact.
6. **Keep-list discipline.** Never delete: toolchains (go/, jadx), dictionaries (SecLists, rockyou), venvs, knowledge bases, skill-source repos, DB snapshots, anything with an open file handle. Borderline small item? Keep it and disclose.
7. **Shared-host scope is explicit — default own cases only; an explicit whole-root order overrides it.** If the owner has seen the per-case inventory and says 「全部都清」/「整个 /root/cases 全删」, that covers other operators' case dirs too. Confirm the exact path and irreversible consequence **once**, then execute the whole path. Do not silently downgrade it to "only ours", and do not re-ask after confirmation. Conversely, 「清一下没用的」 without a path is **not** authorization to cross into other tenants' cases.


## 目标材料下线(换目标 / 「删除干净 这些都不需要」)

换目标后老板常紧接一句「删除干净 这些都不需要」。默认范围 = **他刚点名的那一批**,不是全部历史目标: 没说到的旧案卷先留着并如实报「未点名未动」,他补一句再删(实录: 先删新目标,老板下一轮才补「gov.mn 这个也要删除」)。

目标材料不只在案卷目录里——完整清扫清单与有界校验法见 `references/target-decommission-sweep.md`(案卷/eng 工作目录/隔离区/tmp 碎屑/工具会话目录/临时解包二进制)。核心纪律: 显式路径逐个 rm、不动知识库与词典、删后做**有界**残留 grep(全 /root 递归会 180s 超时)。

**删完的回话就是台账，不是总结**：逐类报「删了什么（目录数 / cron job 数 / 旧包数 / 零碎类数）+ 释放多少 GB + 唯一剩下什么」。实测本役收尾回了一句「其他没动 / 都清完了」，用户直接回一个「？」要求重列——他要的是清单，不是结论。台账里两件事必须点名：**释放量**，以及那个**含 PII 的归档包**（它是「删干净」的唯一例外，附一行删除命令，不替他决定）。

## 盘点模式(只读) —— 「查看能清除什么」/「看看能清多少」

**「查看」不是「清」: 只盘点、只报数、落一份清单文件,一个 rm 都不发。** 老板要先看见账本才点头。删的授权词是「清掉/删除/清干净/D也清」,不是「查看」。清单里每档都给一句可执行命令,他回一句就能直接开跑。

输出形状(四档 + keep-list + 合计,实测老板认这个):
- **A档 铁定垃圾** — 临时克隆/碎屑/已解压安装包。给「为什么是垃圾」的**证据**而不是感觉: 克隆看 `git -C <d> remote -v` 与正本是否同源、正本是否完好; 重复 DB 用 `sqlite3 file:<db>?mode=ro` 数核心表行数与原库对齐。
- **B档 系统垃圾** — syslog/journal/btmp/apt/uv/pip 缓存,标体积最大的单文件(通常 syslog.1 一个就几百 M)。
- **C档 过期备份/日志** — 旧 tar 备份包(已被 git+skill-backups 取代)、IDE 日志、DB 损坏恢复残留(留最新 1 份)、snap 保留的上一版。
- **D档 待老板点头** — 已吸收的素材包、闲置的大模型/venv(先 `ps aux|grep` 证明无进程在用)。**不擅自归进可删。**
- **禁止触碰** 一行列全 keep-list 目录名,让他一眼确认没动知识库/词典/案卷/loot。
- **合计** 两行: A+B+C 能放多少 G → 可用空间前后对比; 加 D 档又是多少。

扫描与用量口径、判定命令、清单模板见 `references/disk-inventory-audit.md`(含本机实测 2026-10-25 一轮: 33G 用量里 8.3G 可直接清、2.4G 待点头)。

## 全文导航（已拆分）

主卡保留前 1 节；其余 6 节在 `references/full.md`：

- Workflow
- Git repo bloat — the one case where deleting frees NOTHING
- Delivery + follow-through
- Aggressive defaults (user:「清理干净 没有用的」/ 清盘默认激进)
- Pitfalls (all observed in the field)
- Files

加载：`skill_view(name='safe-bulk-cleanup', file_path='references/full.md')`

> 全文较大（35833 字符），已分 4 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
