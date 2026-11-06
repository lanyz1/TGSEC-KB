---
name: engine-distill
description: >-
  测绘引擎整库蒸馏：盘点 Skill / Playbook / 工具 / 路由覆盖。
  触发：蒸馏整个仓库、整库蒸馏、盘点技能、三件套缺口、engine_distill、orphan_biz。
  张数以本卡命令为准，禁止手改 AGENTS。技能怎么写走 skill-engineering。
---

# 测绘引擎整库蒸馏

## 真源

- `docs/playbooks/测绘引擎整库蒸馏.md`
- `docs/playbooks/公开仓对照补强手法.md`（外界话题 → 本库三件套，不抄正文）
- `docs/learning/README.md`（知识层目录）
- `python3 tools/ops/engine_distill.py snapshot`
- `python3 tools/ops/skill_catalog.py doctor`

```bash
python3 tools/ops/engine_distill.py snapshot
python3 tools/ops/skill_lane.py
python3 tools/ops/engine_distill.py orphans
python3 tools/ops/skill_catalog.py doctor
python3 tools/ops/skill_catalog.py validate
```

`grades.full` 只是「挂了手册+工具」。打站洞看 `lanes.attack_paper`，不要跟收编/百科混刷。真源：`docs/playbooks/打站卡与库存分闸.md`。

不扫 `00-工作台/`、`清晰入口/`、`站点详情/`、`成功站点报告/`、`exports/`。
不读 `config/scope.company.json` 正文。
