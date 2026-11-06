<!-- archived from /root/.hermes/skills/security/engagement-dag-dryrun/SKILL.md on 2026-10-21 -->

---
name: engagement-dag-dryrun
description: "Use when 把重复作业固化成可校验 DAG + dry-run。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/engagement-dag-dryrun`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/engagement-dag-dryrun/…')`，不要相对 `references/legacy/` 解析。

# 作业流 DAG 与 dry-run（把流程从文字变成可校验的图）

借鉴 ShengRenHacker/CyberStrikeAI 的 workflow 引擎（`internal/workflow/` + `docs/zh-CN/workflow-graph.md`）：
节点化 → 保存时严格校验 → dry-run 预演 → 高危自动插审批 → 断点续跑。

## 为什么要（我们的痛点）
1073 张卡解决了「怎么做」，但「一场作业按什么顺序做、哪步没做」散在文字/脑子里；
长时无人值守、接手别人案卷、多目标并行时必然漏步。把 SOP 固化成图，漏洞一览无遗。

## 定义格式（落 `<案卷>/flow.json`）

```json
{"id":"first-day-recon","nodes":[
  {"id":"s",    "type":"start"},
  {"id":"recon","type":"tool",  "tool":"httpx",  "in":["s"], "out":["assets"]},
  {"id":"class","type":"agent", "agent":"recon-classifier", "in":["assets"]},
  {"id":"gate", "type":"condition","expr":"high_risk_port_found", "in":["class"]},
  {"id":"hitl", "type":"hitl", "approver":"user", "in":["gate"]},
  {"id":"out",  "type":"output","template":"首日侦察小结", "in":["hitl","class"]}
]}
```

节点类型：`start / tool / agent / condition / hitl / output / end`。

## 硬校验（保存/开跑前必过，缺一不可）
1. ≥ 1 个 `start` **且** ≥ 1 个 `output|end`；
2. `start` 无入边；`output|end` 无出边；
3. **无环**（拓扑排序能跑通）；
4. `tool` 节点必须有 `tool` 名，`agent` 节点必须指名角色/卡；否则拒绝（它的原设计：未匹配到工具就降级并在 audit 里提示缺字段）；
5. 产物不丢：每个节点的输出必须有下游消费，或显式标记为 sink；
6. **高危语义节点后面必须紧跟 `hitl`**：执行/删除/封禁/爆破/资金/停机类，否则拒绝保存。

## dry-run 纪律
- 预演**只走数据流**：不真跑工具/Agent/审批，只打印「将要执行什么 + 缺哪些字段」。
- **试运行通过 ≠ 可以真跑**：真实开跑仍需授权闸 + 用户确认（尤其爆破/资金面）。
- 用自然语言生成草稿后必须人工改——生成器只给骨架，别拿去当 SOP 执行。

## 与已有卡配合
- 节点执行记录落到事实黑板：`python3 tools/ops/case_facts.py add <案卷> --key flow.recon --claim "httpx 跑完 43 资产" --evidence "p1_body_httpx.txt(41KB)"`。
- **断点续跑**：flow 里为每个节点记 `status`，重启后从**第一个未完成节点**继续；禁止整场重跑（重复投入是明确禁忌）。
- 组织面：跳过 `0day/` 这种长时挂单节点，避免整场卡死。

## 最小可用（5 分钟）
不用引擎也能用：把 SOP 写成上面格式的 JSON → 人肉跑第 1–6 条校验 → 写清楚 `flow.json` 并存进案卷 →
每完成一节点往事实黑板敲一条 fact。
