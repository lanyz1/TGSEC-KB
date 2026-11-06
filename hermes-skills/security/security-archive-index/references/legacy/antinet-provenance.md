<!-- archived from /root/.hermes/skills/security/antinet-provenance/SKILL.md on 2026-10-21 -->

---
name: antinet-provenance
description: >-
 测绘引擎·收集系统全链路操作日志，生成可追溯的执行证据链与向量索引，是多智能体系统可观测性与安全审计的底座。
owned: true
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/antinet-provenance`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/antinet-provenance/…')`，不要相对 `references/legacy/` 解析。

# antinet-provenance（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/antinet-provenance/`

溯源（仅标记）：`anbeime/skill-local`

---

# Provenance 留痕 Skill（太史阁）

## 使用方式
- 由各官署在关键操作节点调用（或通过事件总线异步推送），写入证据链。
- 提供按 `trace_id` / 时间窗 / 官署维度的检索接口，支撑审计面板与回滚定位。

## 输入（Input）
- `event`：操作事件，含 `actor`（官署名）、`action`、`target`、`timestamp`、`trace_id`
- `payload`：（可选）与事件关联的结构化产物引用

## 输出（Output）
- `evidence_chain`：按 trace_id 串联的可追溯证据链
- `vector_index`：用于语义检索的向量索引条目
- `query_api`：按条件检索历史证据的接口描述

## 依赖（Dependencies）
- Qdrant（向量存储，经 MCP 接入）
- SQLite（结构化事件落地，本地兜底）
- 各官署的事件上报协议（统一 schema）

## 失败处理（Failure Handling）
- 向量库写入失败 → 本地 SQLite 缓存事件，恢复后异步补写，不阻塞主流程。
- 单条事件 schema 非法 → 记录并丢弃该条，不影响整链写入。
- 检索超时 → 返回最近一次成功快照并标注 `stale`。

## 复用价值（Reuse Value）
- 可观测性底座：任何多 Agent 系统都能直接挂载，获得开箱即用的审计与回放能力。
- 契合评审：Agent Infra 赛道「工程落地与运行验证及安全审计（20%）」维度的天然得分点。

## 复赛代码包执行（runnable package）
- 真实入口：`scripts/run_provenance.py`
- 执行等价于 `core.runtime.AgentSession.run_stage("provenance")`，调用 `memory.taishige.TaiShiGeAgent.writeback`（把全链路事件与四色卡片回流证据链，纯 Python 可离线）。
- 运行：`python skills/provenance/scripts/run_provenance.py`
- 产物：`examples/snse_survey/provenance/`（trace.jsonl + trace_summary.json，含每一条军机处派发与官署执行事件）。

---

## 在测绘引擎作业中的实际用法

本卡在安全作业中的核心价值：**自动记录每个关键操作步骤，生成可复查的证据链**。

### 操作日志写入

```bash
# 在关键作业节点手动写入操作记录
python3 -c "
import json, time, hashlib
from pathlib import Path

CASE = '<案卷>'
EVIDENCE_DIR = f'exports/bot-recovery/{CASE}/provenance/'
Path(EVIDENCE_DIR).mkdir(parents=True, exist_ok=True)

event = {
 'trace_id': hashlib.md5(f'{CASE}{time.time()}'.encode()).hexdigest()[:8],
 'actor': 'cursor-agent',
 'action': 'api_probe', # 操作类型：api_probe / auth_test / data_read / pay_test
 'target': 'https://<目标>/api/login',
 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
 'result': 'L2_confirmed', # L1/L2/L3
 'payload_ref': 'recon/login_test.json', # 关联证据文件
 'notes': '弱口令 admin:admin123 登录成功'
}

# 追加到 trace.jsonl
with open(f'{EVIDENCE_DIR}/trace.jsonl', 'a') as f:
 f.write(json.dumps(event, ensure_ascii=False) + '\n')
print('Event recorded:', event['trace_id'])
"

# 查询特定案卷的操作时间线
python3 -c "
import json
from pathlib import Path

CASE = '<案卷>'
trace_file = f'exports/bot-recovery/{CASE}/provenance/trace.jsonl'
if Path(trace_file).exists():
 with open(trace_file) as f:
 for line in f:
 event = json.loads(line.strip())
 print(f'[{event[\"timestamp\"]}] {event[\"actor\"]} -> {event[\"action\"]} @ {event[\"target\"]} = {event[\"result\"]}')
else:
 print('No trace file found for case:', CASE)
"
```

### 证据链完整性验证

```bash
# 验证案卷的证据文件完整性（对所有 JSON 文件做 hash）
python3 -c "
import hashlib, json
from pathlib import Path

CASE = '<案卷>'
case_dir = Path(f'exports/bot-recovery/{CASE}')
manifest = {}
for f in case_dir.rglob('*.json'):
 content = f.read_bytes()
 manifest[str(f.relative_to(case_dir))] = hashlib.sha256(content).hexdigest()

# 保存 manifest
with open(case_dir / 'provenance/manifest.json', 'w') as out:
 json.dump(manifest, out, indent=2, ensure_ascii=False)
print(f'Manifest created: {len(manifest)} files')
"
```
