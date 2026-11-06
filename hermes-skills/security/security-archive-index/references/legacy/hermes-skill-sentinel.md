<!-- archived from /root/.hermes/skills/security/hermes-skill-sentinel/SKILL.md on 2026-10-21 -->

---
name: hermes-skill-sentinel
description: >-
  测绘引擎·Hermes 技能库自监控哨兵。用户提到 Hermes 边跑边总结 skill、
  外门技能自动收编、监控技能库、补齐测绘引擎、策展器流水 curator_ledger、
  skill 增量、自动 ingest、哨兵巡检时使用。
  真源 tools/ops/hermes_skill_sentinel.py；底层三源扫描与收编走 hermes_intake.py。
  长跑监控骨架见 长跑监控与哨兵作业链手法.md；打站仍走专卡。
---

> 归档卡：原目录 `/root/.hermes/skills/security/hermes-skill-sentinel`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hermes-skill-sentinel/…')`，不要相对 `references/legacy/` 解析。

# Hermes 技能库自监控哨兵

Hermes agent 在跑任务时会边做边把经验总结成 skill（写 profile 层）。本卡负责
**监听这些新长出来的卡，自动过收编链补进测绘引擎**，并把增量记进案卷流水。

只读 Hermes 源；产物全部落在本库。不改 Hermes 侧任何文件。

## 立刻跑

```bash
# 只看增量（无变化静默零输出，有变化才展开）
python3 tools/ops/hermes_skill_sentinel.py check
python3 tools/ops/hermes_skill_sentinel.py check --json          # 机器可读
python3 tools/ops/hermes_skill_sentinel.py check --exit-on-new   # 有新增作业卡返回 10

# 收编：scan → ingest → skill_own → map，并更新基线
python3 tools/ops/hermes_skill_sentinel.py sync            # 空跑预演
python3 tools/ops/hermes_skill_sentinel.py sync --apply    # 真正落盘

# Hermes 策展器最近动作（带 session_id，看它边做任务边总结啥）
python3 tools/ops/hermes_skill_sentinel.py ledger --n 30

python3 tools/ops/hermes_skill_sentinel.py status          # 基线/流水状态
python3 tools/ops/hermes_skill_sentinel.py report          # 重生成增量报告
python3 tools/ops/hermes_skill_sentinel.py watch --interval 1800
python3 tools/ops/hermes_skill_sentinel.py install --interval 30   # Windows 计划任务
python3 tools/ops/hermes_skill_sentinel.py install --uninstall
```

## 收编链顺序（铁律，不能颠倒）

```
scan → ingest → skill_own → map
```

- `ingest` 把卡拷进 `docs/learning/skill-store/skills/` 并更新 `catalog.json`。
- `skill_own` 再把 store 里的卡装成 `.cursor/skills/<slug>`（`pack: survey-skill`）。
  **有变更卡时哨兵自动带 `--regen`**，把 Hermes 追加过坑的已存在卡也刷新回本库；
  否则只收新卡、变更卡停在旧版。
- `map` 只给**已存在于 `.cursor/skills`** 的 slug 补 `se_skill_route.MAP`。
  **所以 skill_own 必须在 map 之前**，否则 MAP 收不到新条目（会静默漏掉）。
- 收编完跑 `python3 tools/ops/skill_catalog.py doctor` 校验。

## Hermes 策展器流水（最精准增量）

`%LOCALAPPDATA%\hermes\profiles\*\skills\.curator_ledger.jsonl` 记录每次 skill 动作，
带**逐文件 sha256 + session_id**：

| action | 含义 |
|---|---|
| `create` | 新卡诞生 |
| `patch` | 现有卡被追加/改写（通常 SKILL.md） |
| `write_file` | 新增 reference / script，`evidence.file_path` 给相对路径 |

哨兵按**行偏移**增量读，只报上次 sync 之后的新动作；这也是「Hermes 正在补哪张卡、
在哪个会话里补的」的实证来源。指纹 diff 负责兜底（源侧删卡、架构变化）。

## 静默协议

哨兵只对**变化**发声（见 `长跑监控与哨兵作业链手法.md` §2）：

- 无变化：`check` 零输出；`--verbose` 才打一行。
- 有新作业卡才展开「技能 / 源 / 类目 / KB」。
- 首次 `sync --apply` 只建基线，**不把存量卡当新增刷屏**。
- 流水追加到 `exports/hermes-intake/ledger.jsonl`，报告写 `sentinel_report.md`。

## 坑

1. `ccpanes-*` 与 `.` 开头是仓库明确排除的工作区类，不进收编（`_uncollected` 已滤）。
2. Hermes 刚写的卡可能不完整 —— `--min-age 120`（默认）让太新的卡下轮再收。
3. Windows 控制台 GBK 会把中文打成乱码，**报告以文件为准**；命令前加
   `$env:PYTHONIOENCODING="utf-8"` 可让终端也正常。
4. 新卡若命中「窄卡」特征（`cve-xxxx-xxxx`、`-1day`），进报告「待并卡审查」，
   按情报链铁律**类级合并进现有家族卡**，不要新建碎卡。
5. 本哨兵只搬卡，**不扩 scope**；从技能里看到的目标域名不自动进 `targets`。

## 真源

- 引擎：`tools/ops/hermes_skill_sentinel.py`
- 三源扫描 / 底层收编：`tools/ops/hermes_intake.py`（`scan|sessions|digest|ingest|map|cron`）
- 装卡 / 分层：`tools/ops/skill_own.py` · `tools/ops/skill_prune.py`
- 状态 / 报告 / 流水：`docs/learning/skill-store/hermes/sentinel_state.json` ·
  `sentinel_report.md` · `exports/hermes-intake/ledger.jsonl`
- 姊妹卡：`长跑监控与哨兵作业链手法.md` · `monitoring-pipeline-ops` · `remote-daemon-ops`
