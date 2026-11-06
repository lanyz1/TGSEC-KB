<!-- archived from /root/.hermes/skills/security/case-fact-blackboard/SKILL.md on 2026-10-21 -->

---
name: case-fact-blackboard
description: "Use when 跨会话保事实/抗压缩: 案卷事实黑板 fact_key+置信度。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/case-fact-blackboard`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/case-fact-blackboard/…')`，不要相对 `references/legacy/` 解析。

# 案卷事实黑板（抗压缩的跨会话事实图）

借鉴 ShengRenHacker/CyberStrikeAI 的 `project blackboard`：**事实落在案卷里，不落对话里**；上下文只注入索引，细节按需取全文。

## 为什么必须有
- 压缩摘要必然丢细节，而**摘要当证据就是幻觉源头**（`case-progress-consolidation` 已为「凭记忆重写历史数字」付过代价）。
- 换会话/断点续跑时靠回忆重建事实必然走形，用户会立刻发现（「上面的数字不对」）。

## 落地工具

```bash
C=<案卷目录>
python3 tools/ops/case_facts.py init  "$C"
python3 tools/ops/case_facts.py add   "$C" --key panel_path \
  --claim "后台入口 /admin/login?op=login" --status confirmed --conf 0.9 \
  --evidence "p3_body_admin.json(48KB)" --link site=xeelee.top --tag auth
python3 tools/ops/case_facts.py conf  "$C" --key panel_path --status refuted --conf 0.1 --evidence "复测 404"
python3 tools/ops/case_facts.py index "$C"      # 注入上下文用：仅 key+摘要+状态
python3 tools/ops/case_facts.py get   "$C" panel_path   # 写结论前必须取全文
python3 tools/ops/case_facts.py stats "$C"      # 点名「无证据指针」的 fact
```

存储：`<案卷>/facts.jsonl` —— **只追加、带修订历史**，禁止编辑或覆盖式重写（`conf` 子命令即修订）。

## 硬规则
1. **索引不等于事实**：上下文里只有 `fact_key + summary`；写结论/交付前必须 `get` 取全文，禁止凭摘要臆造细节。
2. `--evidence` 为空的事实**不得当结论用**；`stats` 会点名，要么补证据指针（文件名+字节/行数/字段数），要么降到 `provisional`。
3. 状态五态**不得合并**：`provisional / confirmed / refuted / stale / void`（换环境后旧结论置 `stale`，作废批次置 `void`）。
4. `conf` 是置信度、不是证据；`conf>=0.9` 才够格 `confirmed`，且必须有 evidence。
5. 事实必须挂**关系边**（`--link site=/host=/parent=`），后续靠边扩散找同族资产，别再翻聊天记录。
6. **同会话跨压缩同样适用**：不只在换会话时——同一会话内上下文压缩后，「事实」同样只认 `facts.jsonl`、不认残存记忆；继续任何攻坚前先 `index` 回读。压缩后的自己 ≈ 刚换班的同事，交接一步不能省。

## 置信度更新（贝叶斯直觉，够用版）

```
odds = conf / (1 - conf)          # 先验转赔率
odds *= LR                        # 每条独立证据乘一次似然比
conf = odds / (1 + odds)          # 回读
```

| 证据 | LR |
|---|---|
| 现场复现 / 服务端原文 / 抓包 | 5–10 |
| 客户端单侧行为 / 文档自述 | 1.2–2 |
| 仅推断 / 他站类比 | 1.05 |
| 明确反证（复测失败、环境已变） | 0.1–0.5 |

**独立才相乘**：同一条证据换个包装重复使用只算一次（不许把一份 body 数三遍把 conf 抬到 0.99）。

## 与已有卡的分工
- `hypothesis-ledger`：**候选假设**（未定论，驱动下一动作）
- 本卡：**已定事实**（含否证，跨会话留存，支撑交付与续跑）
- `case-progress-consolidation`：交付前全局对账（读本卡 + 磁盘产物）
- `agent-evidence-gate`：结案闸（够不够格写「无路」）

## 自测

```bash
python3 tools/ops/case_facts.py add  D:/tmp/x --key t --claim "a" --conf 0.5
python3 tools/ops/case_facts.py index D:/tmp/x   # 期望：1 条，?/0.50
python3 tools/ops/case_facts.py get  D:/tmp/x t  # 期望：含 claim/ts/修订次数
```
