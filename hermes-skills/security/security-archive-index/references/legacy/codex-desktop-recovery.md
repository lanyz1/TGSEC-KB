<!-- archived from /root/.hermes/skills/security/codex-desktop-recovery/SKILL.md on 2026-10-21 -->

---
name: codex-desktop-recovery
description: >-
  测绘引擎·Use when Codex 桌面App会话列表空了/历史会话丢失. 重建UI索引库.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/codex-desktop-recovery`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/codex-desktop-recovery/…')`，不要相对 `references/legacy/` 解析。

# codex-desktop-recovery（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/codex-desktop-recovery/`

溯源（仅标记）：`hermes/autonomous-ai-agents`

---

# Codex 桌面版会话恢复 (Desktop App / Store 版)

Codex 桌面 App（Microsoft Store 安装，进程名 `ChatGPT.exe` + 子进程 `codex.exe`）的
**UI 会话列表**和**实际会话数据**是分开存储的。UI 列表空 ≠ 数据丢 —— 90% 的情况是
UI 索引库 `sqlite/codex-dev.db` 的 `local_thread_catalog` 表被重建/损坏，而真实数据
完好躺在数据层里。本技能用于诊断并修复这种情况。

## 触发条件

- 用户说"Codex 会话全没了 / 历史会话列表空了 / 会话内容丢失"
- App 更新/重装后侧边栏列表只剩几条旧记录
- 需要确认 Codex 桌面版会话数据是否可恢复

## 数据布局（CODEX_HOME = C:\Users\Administrator\.codex）

| 文件 | 角色 | 判断依据 |
|---|---|---|
| `sessions/YYYY/MM/DD/rollout-*.jsonl` | **真实会话内容**（源头真相） | 文件数 ≈ 会话数 |
| `state_5.sqlite` → `threads` 表 | 线程元数据主库（title/source/archived/rollout_path） | `COUNT(*)` = 全部线程（含 subagent） |
| `session_index.jsonl` | 旧版 UI 索引（每行 `{"id","thread_name","updated_at"}`） | 60 条左右 |
| `sqlite/codex-dev.db` → `local_thread_catalog` 表 | **UI 侧边栏列表的数据源**（新版） | 若只剩几条 → 列表空 |
| `logs_2.sqlite` → `logs` 表 | app-server(Rust) 日志 | 铁证：`Resumed rollout with N items, parse errors: 0` |
| `AppData/Local/Codex/Logs/YYYY/MM/DD/codex-desktop-*.log` | Electron UI 日志 | thread/list 请求记录 |

关键区分：**app-server(Rust) 读 `state_5.sqlite`；Electron UI 读 `sqlite/codex-dev.db` 的 catalog**。
两条链路独立，别修错库。

## 诊断步骤

1. 数真实数据：
   ```bash
   find ~/.codex/sessions/ -name "*.jsonl" | wc -l
   ```
   （正常几十到上百条，按日期分目录）
2. 对比元数据：
   ```sql
   SELECT COUNT(*) FROM threads;                       -- 全部
   SELECT COUNT(*) FROM threads WHERE thread_source='user' AND archived=0;  -- UI 应显示的
   ```
3. 对比 UI 索引（**关键一步**）：
   ```sql
   SELECT COUNT(*) FROM local_thread_catalog;
   SELECT * FROM local_thread_catalog_sync_state;      -- initial_build_complete=0 → 索引构建失败
   ```
   catalog 条数 << threads 用户线程数 → 确诊为索引问题，数据未丢。
4. 找铁证（可选）：`logs_2.sqlite` 里搜 `Resumed rollout with`，看到 `parse errors: 0`
   即证明会话内容完整可读。UI 端日志在 `~/AppData/Local/Codex/Logs/` 下按日期分目录。

## 修复步骤（重建 local_thread_catalog）

1. **备份**：`cp codex-dev.db codex-dev.db.bak-$(date +%Y%m%d)`（连同 state_5.sqlite、
   session_index.jsonl 一起备份）。
2. **先杀 App**（catalog 被占用时写入会失败/被覆盖）：
   ```bash
   powershell.exe -NoProfile -Command "Stop-Process -Name 'ChatGPT','codex' -Force -ErrorAction SilentlyContinue"
   ```
   ⚠️ MSYS/git-bash 里 `taskkill //F //IM` 会报 "Invalid argument" —— 直接用 PowerShell
   `Stop-Process`，别在 taskkill 上浪费时间。
3. **回填 catalog**：运行 `scripts/rebuild_thread_catalog.py`（从 state_5.sqlite 的
   threads 表把 `thread_source='user' AND archived=0` 的线程灌回 local_thread_catalog，
   保持 observation_sequence 递增、更新 sync_state 为 initial_build_complete=1）。
   或手动 SQL：按 catalog 列 `(host_id, thread_id, display_title, source_created_at,
   source_updated_at, cwd, source_kind, source_detail, model_provider, git_branch,
   observation_sequence, missing_candidate, thread_source)` 逐条 INSERT；
   observation_sequence 必须 > 现有 max 与 sync_state 中的值。
4. **校验**：`PRAGMA integrity_check` 必须返回 `ok`；抽查每条 catalog 记录的
   rollout_path 对应文件存在。
5. **重启 App**：
   ```bash
   powershell.exe -NoProfile -Command "Start-Process 'explorer.exe' -ArgumentList 'shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App'"
   ```
   AppUserModelID 可用 `Get-StartApps | ? {$_.Name -match 'Codex|ChatGPT'}` 查。
6. 重启后等 10~15s，在 `~/AppData/Local/Codex/Logs/` 最新日志里 grep `thread/list`
   确认 UI 重新拉取列表；`sqlite/codex-dev.db` 无 -wal/-shm 残留写锁即为安全。

## 陷阱

- **不要只查 sessions/ 就下结论**：会话文件在 ≠ UI 能显示。必须查 local_thread_catalog。
- **别在 App 运行时改 codex-dev.db**：先杀进程再写，写完再启动。
- **observation_sequence 必须递增**：低于或等于现有值会被 UI 当作旧记录忽略。
- `logs_2.sqlite` 的 `ts` 字段是**本地时间**（不是 UTC），跨时区排查时别换算错。
- 用户在意的是"会话还在不在"——先给结论（数据没丢），再动手修，别让用户干等。

## 关联

- 桌面版 CLI 用法（exec/resume/PR）见 `codex` 技能。
- App 闪退/崩溃类问题见 `windows-app-crash-diagnosis`。
