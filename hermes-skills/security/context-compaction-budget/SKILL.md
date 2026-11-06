---
name: context-compaction-budget
description: "<中文，触发优先、120-260 字：长作业把上下文跑到几十轮、摘要越压越糊、已证结论被压掉要找回来、要算窗口与输出预留时加载。给单会话长任务一套压缩闸门：输入/输出预算公式、minor 与 major 两级触发阈值、冷却与单次上限、digest 预算与关闭思考、旧 digest 签名复用与失效、冷节点邻域保留、历史回放双限、溢出只恢复一轮。附本机落地做法：每个收口往账本追加结论事件，上下文丢了账本还在。>"
sources: art-content, operator_experience
---

# CONTEXT COMPACTION BUDGET — 长作业的压缩闸门

> 一句话：压缩不是「塞进摘要」，是**按预算切、按签名去重、按两级节流**。压掉的必须是废探索，留下的必须是已证事实，而「留下」的落点是账本不是摘要。

## 1. 三个预算量（先算窗口再谈压缩）

| 量 | 公式 / 取值 | 作用 |
|---|---|---|
| 输入预算 `inputBudget` | `window − outputBudget − min(8192, max(128, window/20))` | 真正给历史消息的空间 |
| 输出预算 `outputBudget` | `min(配置值, 32768, 请求 MaxTokens)`，默认 `8192` | 给模型本轮回复留位 |
| 窗口兜底 | 窗口 ≤0 时按 `200000` 算 | 拿不到真实窗口时的保守值 |
| 安全垫 | `min(8192, max(128, window/20))` | 20% 窗口兜底，上限 8192 |

判据：`inputBudget` 用完就是压缩触发线，不是「感觉差不多了」。

## 2. 两级压缩与节流

| 参数 | 值 | 语义 |
|---|---|---|
| minor 触发 | ≥ **20** 条消息 | 轻压：只并对话尾巴，保留近因 |
| major 触发 | ≥ **8** 个 digest | 重压：合并/替换历史 digest |
| 冷却 | **60s** | 两次压缩之间最短间隔，防抖动 |
| 单次上限 | **5min** | 一次压缩最多跑 5 分钟，超时按未压缩处理 |
| digest 预算 | `MaxTokens=1500` | 摘要长度上限 |
| digest 思考 | `disabled` | 摘要**不许**做推理，只做压缩 |

major 的关键动作：用 `blockSignature`（块内容指纹）复用签名一致的旧 digest，签名变了的新建，过期 digest 先 `SupersedeDigests` 再写新的。判据：同一段历史被压两次不许产出两份互相矛盾的摘要。

## 3. 历史回放双限

| 参数 | 值 | 作用 |
|---|---|---|
| 回放上限 | `min(16000, limit/4)` | 回放旧消息最多吃掉 1/4 预算 |
| 近因窗口 | `MaxRecentExchanges = 20` | 最近 20 轮完整保留 |
| 摘要预算 | `MaxTokens=2048` | 回放用摘要的长度 |
| 摘要调用上限 | 12 次 | 一场压缩最多调 12 次模型 |
| 摘要自检 | ≤ 2200 tokens | 自查超标就截断，不长回去 |
| 溢出恢复 | 只一轮 | `limit /= 2`，`keepTokens` 再 `/2`，一轮没恢复就报错，不做递归重试 |

## 4. 冷节点邻域（R/K 保留）

长作业的探索图会无限膨胀。保留口径 `R=6`、`K=2`：

- 从当前节点出发只保留 **6 跳**邻域，超出的折叠成一句「更早的探索已折叠」。
- 每跳只留 **2 条**代表边（最新 + 最相关），其余边丢弃但保留计数。
- 折叠不删账本：节点与边在 `case/ledger.jsonl` 里有事件，需要时按 id 取回。

## 5. 本机落地：digest 落账本，不落上下文

| 动作 | 命令 |
|---|---|
| 每个收口写一条结论 | `ledger.cmd intent close .\case-<date> I3 --outcome "已证：换 id 返回他人资料"` |
| 每条发现入库 | `ledger.cmd finding add .\case-<date> --title "..." --severity high --endpoint "..." --hyp H1` |
| 证据绑完再压 | `ledger.cmd evidence bind …` 之后 `verify` 仍能跑 |
| 压完取回 | `ledger.cmd status .\case-<date>` / `ledger.cmd verify .\case-<date>` |

判据：一次压缩之后，`verify` 的判据集合不许变——变了说明压掉了账本依赖的事实，这一压是坏的。

## 6. 失败模式与判据

| 症状 | 判据 | 处置 |
|---|---|---|
| 摘要越压越糊 | digest 里出现新推理、新数字 | 关 thinking、限 1500 tokens、只允许复述 |
| 已证事实丢失 | 压缩后 `verify` 从 exit 0 变 exit 1 | 结论事件先落账本再压 |
| 压缩抖动 | 60s 内触发两次 | 冷却窗口，第二次排队 |
| digest 互相矛盾 | 同 `blockSignature` 两份摘要 | 签名复用 + Supersede 旧 digest |
| 长摘要挤爆回放 | 回放 > `limit/4` | 近因窗口 20 轮 + 摘要 2048 |
| 无限递归重试 | 溢出恢复跑了两轮 | 只允许一轮，第二轮直接报错 |

## 7. 与既有卡衔接

| 场景 | 卡 |
|---|---|
| 侧问题不进主上下文、独立预算 | [side-question-context-budget](../side-question-context-budget/SKILL.md) |
| 结论/证据/版本的落点 | [engagement-ledger-v2](../../redteam-framework/engagement-ledger-v2/SKILL.md) |
| 多角色交接时谁记什么 | [autonomous-pentest-agent-architecture](../../redteam-framework/autonomous-pentest-agent-architecture/SKILL.md) |
