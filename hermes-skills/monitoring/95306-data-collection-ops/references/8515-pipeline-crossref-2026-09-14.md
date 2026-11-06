# 8515/b580 索引链 → 参照 monitoring-pipeline-ops(2026-09-14)

本系统 8515 匿名流 → index.json → audit_diff → 定向刷新 的全链知识(2026-09-14 夜修)在 `monitoring-pipeline-ops` 技能:

- `references/8515-index-starvation-and-pipeline-cadence-2026-09-14.md` — 三重根因(命名失配 b580 未入索引 / 机器快照死胡同 / 800行地板)+ v9.34/35 修复 + 全链频率表 + 排障口诀。
- `references/8515-backfill-sweep-and-open-items-2026-09-14.md` — 回填落地判据(51,457 项目结果回写)+ 手动全量刷新 sweep 配方 + 审计反查/未审批语义。
- `scripts/manual-full-refresh-sweep.py` — 手动 sweep 脚本(7 步, 主服后台跑)。

要点速记: 快照 2h/≤1万行(v9.34=525edd50); b580 每 30 分钟入索引(v9.35, `.b580_seen.json` mtime 防重); 端到端 平台变更→池 ≈10~15 分钟; "未审批"=平台终态非陈旧; 补验队列 800+ 账号每日重建。
