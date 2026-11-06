---
name: agent-evidence-gate
description: >-
  测绘引擎证据闸：口头结论对案卷原文、近成功不准结案、
  批量 HTTP 对照、highlight 源码还原。
  用户提到证据闸、口头结论、结案、无路、same-body、http_probe_batch、
  highlight_file、source_extract、变体对照时使用。
  只读闸门不打点；对照/还原要对授权 URL。交差仍先 case-review。
---

# 证据闸与对照还原

工具原文才是证据。高信号没耗尽不准判死。本卡不替代专链，只闸结案、对照变体、还原着色页。

## 立刻跑

```bash
python3 tools/ops/case_review.py --case exports/bot-recovery/<案卷>
python3 tools/ops/object_matrix.py check --case <案卷> --strict
python3 tools/ops/evidence_gate.py --case <案卷> --from-status
python3 tools/ops/case_ledger.py verify --report <案卷>

python3 tools/ops/http_probe_batch.py --base https://授权站 --case <案卷> \
  --variant '{"label":"clean","path":"/","params":{"id":"1"}}' \
  --variant '{"label":"probe","path":"/","params":{"id":"1 OR 1=1"}}'

python3 tools/ops/source_extract.py --url https://授权站 --case <案卷>
```

## 档位

| 信号 | 档 | 动作 |
|------|----|------|
| 对照有 DIFF / 抽出 sink | L1 | 记 JSON，交接专卡 |
| DIFF 被注入/越权/LFI 复现 | L2 | 专卡 findings + 本卡 JSON |
| 准备写结案 / 无路 | 闸 | leftover sink/表单/DIFF → 继续打 |
| 有身份 | 矩阵 | 先填 `测绘/object_matrix.md`，专卡阴性回表 |

## 近成功闸（强制）

证据里还有这些之一，不得写「无路 / 结案」：

- 源码 sink（`eval` / `unserialize` / `php://filter`）
- 表单 / 参数面未对照
- `http_probe_batch` 的 DIFF 未解释
- Actuator / JWT / 登录面未按专卡打完
- 对象矩阵仍有「未测」

## 失败

- 闸门 FAIL → 撤回口头结论或补真实输出
- 对照全 SAME → 换面或 `core_web_surface_probe`，不是注入阴性
- 还原无 sink → `sensitive-dir-dump` / `lfi-rfi-exploit`

## 真源

- 手法：`docs/playbooks/编解码对照与证据闸手法.md`
- VulnClaw 已并入：`docs/playbooks/VulnClaw融合升级手法.md`
- 工具：`python3 tools/ops/evidence_gate.py --help`
- 对照：`python3 tools/ops/http_probe_batch.py --help`
- 还原：`python3 tools/ops/source_extract.py --help`


---

## 外部库增量（2026-10-11 分享包）

## 收尾契约（能不能宣布「完成」）

「完成」是运行时事件，不是自然语言。写结案/宣布成功前，先在口头/心里填这份结构（源自成熟 Agent 平台的 finalization contract，我们按本库口径收敛）：

| 字段 | 本库填法 |
|---|---|
| `status` | in_progress / completed / blocked / failed / cancelled |
| `evidence_verified` | 现场复现或服务端原文？否则 false |
| `evidence_refs` | 磁盘文件名 + 字节/行数（不是「上面那段输出」） |
| `pending_tool_runs` | 还有后台任务在跑？ |
| `pending_plan_steps` | 对象矩阵/专卡还有「未测」格？ |
| `pending_approvals` | 用户尚未拍板的动作？ |
| `missing_checks` | 未复跑的批次、未对照的参数面 |

硬规则：`evidence_verified=false` 时不得把候选输出写成已验证结论；`pending_*` 任一非空时不得 `completed`。
细节与示例见 `references/finalization-contract.md`。
