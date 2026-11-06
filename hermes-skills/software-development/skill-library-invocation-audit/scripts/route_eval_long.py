#!/usr/bin/env python3
"""长任务/长跑作业场景的现场口语检索评测。"""
import json, subprocess, sys

EVAL = [
    # 长跑 / 无人值守 / 汇报节奏
    ("长时间跑 队列 怎么汇报 进度", ["long-run-engagement-discipline", "pentest-campaign-discipline", "pentest-campaign-ops"]),
    ("无人值守 渗透 半夜 自己跑", ["long-run-engagement-discipline", "pentest-campaign-discipline", "remote-daemon-ops"]),
    ("跑了几万发 全 0 怎么交代", ["long-run-engagement-discipline", "pentest-campaign-ops", "operator-discipline"]),
    ("单发 冷却 别把 目标 打死", ["long-run-engagement-discipline", "pentest-campaign-discipline", "waf-bypass-methodology"]),
    ("队列 跑一半 断了 怎么续", ["long-run-engagement-discipline", "pentest-campaign-ops", "case-progress-consolidation"]),
    ("批量 扫 还在跑 别 自己停", ["long-run-engagement-discipline", "pentest-campaign-ops", "fleet-task-shutdown"]),
    # 收网 / 停机 / 清扫
    ("收网 全机 清进程 停机", ["fleet-task-shutdown", "engagement-teardown", "operator-discipline"]),
    ("战役 暂停 落盘 报告 发文件", ["pentest-campaign-ops", "pentest-delivery-closure", "engagement-teardown"]),
    ("清 后台 进程 别 自杀 pkill", ["fleet-task-shutdown", "remote-daemon-ops", "safe-bulk-cleanup"]),
    # 多机 / daemon / 监控
    ("daemon 保活 setsid 自启动", ["remote-daemon-ops", "fleet-task-shutdown"]),
    ("多机 采集 主服 合并 监控", ["monitoring-pipeline-ops", "remote-daemon-ops"]),
    ("跳板机 部署 监控 脚本", ["remote-daemon-ops", "monitoring-pipeline-ops", "internal-tunnel"]),
    # 案卷 / 接管 / 补漏
    ("接手 案卷 补漏 对账", ["case-progress-consolidation", "case-review", "operator-discipline"]),
    ("交差 证据链 能不能 结案", ["case-review", "pentest-finding-verification", "triage-validation"]),
    ("渗透 进度 整理 清单", ["case-progress-consolidation", "pentest-working-report", "operator-discipline"]),
    # 战役编排 / 队列纪律
    ("新目标 作战计划 先打哪", ["campaign-router", "pentest-methodology", "recon-and-methodology"]),
    ("长跑 队列 别 索要 授权", ["long-run-engagement-discipline", "engagement-scope-gating", "operator-discipline"]),
    ("拖库 全量 别抽样", ["userdata-grab", "bulk-data-delivery", "engagement-loot-delivery"]),
    ("大文件 分卷 投递 tg", ["deliverable-packaging", "bulk-data-delivery", "engagement-loot-delivery"]),
    ("战役 复盘 回写 技能", ["ops-review", "arsenal-closure-ops", "skill-pack-absorption"]),
]

phase = sys.argv[1] if len(sys.argv) > 1 else "recon"
rows = []
for q, expect in EVAL:
    r = subprocess.run(["python3", "/root/.hermes/arsenal/skill_find.py", q, "--phase", phase, "--top", "10", "--json"],
                       capture_output=True, text=True)
    try:
        hits = json.loads(r.stdout)
    except Exception:
        hits = []
    names = [h["name"] for h in hits]
    rank = next((i + 1 for i, n in enumerate(names) if n in expect), 0)
    rows.append((q, rank, names[:3], expect))

top1 = sum(1 for _, rk, _, _ in rows if rk == 1)
top3 = sum(1 for _, rk, _, _ in rows if 1 <= rk <= 3)
miss = [r for r in rows if r[1] == 0]
for q, rk, top, exp in rows:
    tag = "OK  " if rk == 1 else ("~   " if rk <= 3 else "MISS")
    print(f"{tag} rank={rk or '-':>2}  {q}   -> {', '.join(top)}")
print(f"\nTOP1 {top1}/{len(rows)}  TOP3 {top3}/{len(rows)}  MISS {len(miss)}/{len(rows)}")
if miss:
    print("\nMISS 明细:")
    for q, rk, top, exp in miss:
        print(f"  {q!r} expect={exp} got={top}")
