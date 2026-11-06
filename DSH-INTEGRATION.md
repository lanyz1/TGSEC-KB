# DSH × TGSEC 融合入口（本机实测口径，2026-11-05）

## 三个物理位置

| 层 | 路径 | 装什么 |
|---|---|---|
| KB 正文 | `C:\Users\Administrator\.dsh\tgsec-kb\` | `domains/` 30 域 38,657 文件 · `hermes-skills/` 2,380 个 `SKILL.md`（唯一 2,348）· `tools/` · `arsenal/arsenal.db` |
| 活跃技能层 | `C:\Users\Administrator\.dsh\skills\` | 31 张：30 张伞形 + `tgsec-arsenal-router` |
| 检索索引 | `C:\Users\Administrator\.dsh\tgsec-kb\arsenal\arsenal.db` | 354 MB / 2,348 卡（启用 574 · 归档 1,774 · legacy 1,856） |

## 开工三步

1. 定面：load `pentest-execution`（活靶纪律、覆盖矩阵、验证门）+ `tgsec-suite`（30 域矩阵）。
2. 找打法：**先检索，再手搓** ——
   ```
   & "C:\Users\Administrator\.dsh\tgsec-kb\tools\cardfind.cmd" "<产品/症状>" --top 8
   ```
   结果 `[E]` 读 `hermes-skills\security\<卡名>\SKILL.md`；`[D]` 读输出行给的 `catalog=...\references\legacy\<卡名>.md`。用法全表在 `tgsec-arsenal-router` 卡。
3. 读正文：`domains\<面>\README.md` → `domains\CASE-INDEX.md` → 同面 `case-lessons\` ≥1 篇 → `playbook-6000/` → `hunter-6000/` → `src-methods/` → `torch-*`。

## 关键索引文件

- `MASTER.md`（30 域导航）· `ROUTING.md`（关键词 → 路径）· `START.md`（新手 3 步）
- `domains\CASE-INDEX.md`（实战课总入口）· `domains\0day-exploits\EXPLOITARIUM-INDEX.md` · `POC-PLATFORM-INDEX.md`
- `docs\updates\UPDATE-2026-11-05.md`（上一轮）· `INGEST-2026-11-05-WINDOWS-INDEX.md`（本次回流账本）

## 维护

```powershell
# 新卡落盘后重建索引（约 95 s）
python.exe C:\Users\Administrator\.dsh\tgsec-kb\tools\arsenal\arsenal_build.py   # 需先设 ARSENAL_SKILLS / ARSENAL_DB
```

@TGSEC社区 · @TGSEC-Qtzuu 整理
