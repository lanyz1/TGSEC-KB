# 长任务 / 长跑作业场景检索评测集（2026-10-22）

前 16 条基线（`route-eval-set-20261022.md`）覆盖的是「单点打法」，没有覆盖**长跑战役的过程管理**：
断点续跑、队列别自己停、无人值守汇报、收网清扫、拖库全量、分卷投递。老板点名「长任务的还没测」后补测。

跑法：

```bash
python3 /root/eval_long.py recon     # auth / injection 各跑一遍
```

## 结果（三个 phase 一致）

| 指标 | 补词前 | 补词后 |
|---|---|---|
| TOP1 | 14/20 | **20/20** |
| TOP3 | 16/20 | **20/20** |
| MISS | 2/20（另 2 条 rank 6/9） | **0/20** |

原 16 条基线同步回归：TOP1 15/16、TOP3 16/16、MISS 0/16 —— 无退化。

## 补的词（只进 tags，不塞通用词）

- `long-run-engagement-discipline`：断点续跑 / 队列续跑 / 队列断了 / 别自己停 / 还在跑 / 批扫 / 长跑队列 / 无人值守
- `pentest-campaign-ops`：断点续跑 / 队列 / 续跑 / 收网 / 长任务
- `userdata-grab`：别抽样 / 全量拖库 / 要全部 / dump所有
- `deliverable-packaging`：分卷 / 大文件投递 / 投递 / 战利品交付
- `bulk-data-delivery`：分卷 / 大文件 / 投递
- `ops-review`：复盘回写 / 技能沉淀 / 战役复盘 / 战后复盘

补词前的失败形态值得记住：

- `队列 跑一半 断了 怎么续` → rank 9，打进 `src-hunt-shortlist`/`shopxo-pentest`（「续」被当成业务词）
- `批量 扫 还在跑 别 自己停` → 完全 MISS，给了 `windows-scheduled-task-ops`/`nuclei-scan`（只认出「扫描」）
- `拖库 全量 别抽样` → rank 6，`userdata-grab` 的 description 有「拖库/全量」但没有「别抽样」这种否定式口语
- `大文件 分卷 投递 tg` → 完全 MISS，`tg-*` 三张卡把「tg」抢光，交付卡中文词一个都没带

**教训**：肯定式关键词（拖库、投递）不等于现场否定式/口语化说法（别抽样、别自己停、断了怎么续）。
每张过程管理卡都要带一组「老板会怎么催 / 怎么喊停」的原话。

## 评测集（20 条）

```json
[
 {"q": "长时间跑 队列 怎么汇报 进度", "expect": ["long-run-engagement-discipline", "pentest-campaign-discipline", "pentest-campaign-ops"]},
 {"q": "无人值守 渗透 半夜 自己跑", "expect": ["long-run-engagement-discipline", "pentest-campaign-discipline", "remote-daemon-ops"]},
 {"q": "跑了几万发 全 0 怎么交代", "expect": ["long-run-engagement-discipline", "pentest-campaign-ops", "operator-discipline"]},
 {"q": "单发 冷却 别把 目标 打死", "expect": ["long-run-engagement-discipline", "pentest-campaign-discipline", "waf-bypass-methodology"]},
 {"q": "队列 跑一半 断了 怎么续", "expect": ["long-run-engagement-discipline", "pentest-campaign-ops", "case-progress-consolidation"]},
 {"q": "批量 扫 还在跑 别 自己停", "expect": ["long-run-engagement-discipline", "pentest-campaign-ops", "fleet-task-shutdown"]},
 {"q": "收网 全机 清进程 停机", "expect": ["fleet-task-shutdown", "engagement-teardown", "operator-discipline"]},
 {"q": "战役 暂停 落盘 报告 发文件", "expect": ["pentest-campaign-ops", "pentest-delivery-closure", "engagement-teardown"]},
 {"q": "清 后台 进程 别 自杀 pkill", "expect": ["fleet-task-shutdown", "remote-daemon-ops", "safe-bulk-cleanup"]},
 {"q": "daemon 保活 setsid 自启动", "expect": ["remote-daemon-ops", "fleet-task-shutdown"]},
 {"q": "多机 采集 主服 合并 监控", "expect": ["monitoring-pipeline-ops", "remote-daemon-ops"]},
 {"q": "跳板机 部署 监控 脚本", "expect": ["remote-daemon-ops", "monitoring-pipeline-ops", "internal-tunnel"]},
 {"q": "接手 案卷 补漏 对账", "expect": ["case-progress-consolidation", "case-review", "operator-discipline"]},
 {"q": "交差 证据链 能不能 结案", "expect": ["case-review", "pentest-finding-verification", "triage-validation"]},
 {"q": "渗透 进度 整理 清单", "expect": ["case-progress-consolidation", "pentest-working-report", "operator-discipline"]},
 {"q": "新目标 作战计划 先打哪", "expect": ["campaign-router", "pentest-methodology", "recon-and-methodology"]},
 {"q": "长跑 队列 别 索要 授权", "expect": ["long-run-engagement-discipline", "engagement-scope-gating", "operator-discipline"]},
 {"q": "拖库 全量 别抽样", "expect": ["userdata-grab", "bulk-data-delivery", "engagement-loot-delivery"]},
 {"q": "大文件 分卷 投递 tg", "expect": ["deliverable-packaging", "bulk-data-delivery", "engagement-loot-delivery"]},
 {"q": "战役 复盘 回写 技能", "expect": ["ops-review", "arsenal-closure-ops", "skill-pack-absorption"]}
]
```
