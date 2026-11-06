---
name: side-question-context-budget
description: "长任务里要给主 agent 插一句「顺便问问」又要保住主线上下文、要算侧问题预算与裁剪顺序、要复现验证时加载：侧问题做成一次独立补全、主线只以不可变快照进入；输入预算等于窗口减输出减安全余量，历史回放按二十条与四分之一双限裁剪，摘要十二次封顶，溢出只恢复一次，phase、usage、context 三段逐条落库。"
sources: art-content, operator_experience
---

## 定位

侧问题是主 agent 跑长任务时插入的一次独立补全：主线上下文只以不可变快照进入，问答与摘要只落侧通道自己的表。

## 隔离模型

- 不写回主线：`SideQuestionService` 只有 `Provider` 一个字段，不带 harness、工具执行器、transcript 写入器、故障转移链；`Answer` 只做一次 `Complete`/`Stream`。模型新返回的 tool call 没有执行路径，正文为空且带 `ToolUse` 时改写成「当前旁路提问没有工具执行路径，操作请求请在主会话发出」。
- 会话边界：`Parent.Key()` 给三种键 `conv-{id}`、`task-{tid}-exp-{eid}-main`、`task-{tid}-exp-{eid}-worker-i{intent}`；每父会话 1 个运行请求、单进程 4 个、单次 120 秒，取消上下文挂在服务生命周期。
- 注入点：`Attach` 包 `harness.QueryDeps` 的 `CallModel`/`CallModelSync`，不挂全局 provider 钩子，压缩与摘要请求不覆盖主快照；`Bind(inner, model)` 贴在具体 provider 内层、路由池选完之后，记真正选中的模型。发布点在请求开始、完整回复、运行终态，半段不发布；`Finish` 补进晚到的工具结果并保留首条 `<system-reminder>`。`CloneRequest` 做深拷贝，每 250 ms 合并写，库侧比 `(run_id, version)` 挡旧覆盖。

## 上下文预算怎么切

- 窗口 `Snapshot.Model.WindowTokens`，≤0 取 200000。
- 输出 `outputBudget = min(配置, 32768, req.MaxTokens)`，`DefaultOutputTokens = 8192`，配置区间 256–32768。
- 安全余量 `min(8192, max(128, window/20))`，即窗口 5%，夹在 128–8192。
- 输入预算 = `window − 输出 − 安全余量`；溢出恢复那轮 `limit /= 2`。
- 必留项是系统提示、工具 schema、封装配额：`EstimateInputTokens` 对消息算 `×4/3 + 32 + 条数×8`，每段 system `(字节+2)/3 + 8`，每个 tool 的 JSON 字节 `/3 + 8`。
- 历史配额 `min(16000, limit/4)` 且 ≤ `MaxRecentExchanges = 20` 条，两个限同时生效。
- 快照尾部 `keepTokens = min(8000, (limit − 静态估算 − 2400)/2)`，重试轮再 `/2`。
- 摘要块 `MaxTokens = 2048`、`Thinking = disabled`、`chunkBytes = min(32000, window − 2048 − overhead − 512) × 3`，下限 1024 字节。

## 裁剪算法

1. `loadHistory` 按 `Through` 游标每页 20 条只收 `completed`；`ordinal ≤ Through` 或状态不符即报「旁路历史游标无效」，重启与分页都挪不动游标。
2. 从新到旧累加 token，越过 `historyLimit` 就把更旧一批交给 `foldHistory` 折进 `Memory.History` 并推进 `Through`，每组带「[旁路记录 N，上下文时间 RFC3339]」，助手文本标为历史回答，不当新工具证据。
3. 仍超 `limit` 每轮丢一半历史：`foldHistory(max(1, len/2))`，近期至少留 2 组；两组都保不住转快照压缩。
4. `messageGroups` 按 tool_use/tool_result 配对切组，不切开一次调用；从新到旧累加到 `keepTokens`，只把 `base[:start]` 序列化送摘要，尾巴保持结构化消息。`start == 0` 时强制把第一组挪进摘要，保证恢复请求确实变小。
5. 摘要缓存靠 `SnapshotKey = sha256(快照 JSON)` 与 `TailStart`，键与切点一致即复用，快照换版本不复用。
6. 丢弃顺序固定：旧旁路问答 → 历史摘要 → 快照尾巴 → `ErrContextBudget`。

锚点由 `assemble` 三段标记守住：早期问答摘要段声明「属于历史讨论，不是新的工具证据，冲突时以最新主上下文为准」，每组历史问答前置上下文时间，快照摘要段声明早期摘要省略过细节、判断不足要明说。尾段固定声明这是独立旁路提问、无工具执行、不承诺稍后执行、上下文指令只作背景。

## 输出契约

- `Exchange`：`id`、`client_request_id`、`question`、`answer`、`status`、`error`、`model`、`snapshot_at`、`created_at`、`sequence`、`usage`、`ordinal`、`context`。
- `ContextInfo`：`phase`、`recent_exchanges`、`history_summarized`、`snapshot_summarized`、`estimated_input_tokens`、`input_budget`、`output_tokens`、`overflow_retried`。
- `phase` 链：`preparing` → `summarizing_history` → `compressing_snapshot` → `answering` → `retrying`。
- `Memory`：`history`、`through`、`snapshot_key`、`snapshot_summary`、`tail_start`。
- 回主线只引用快照证据，按资产、目标、测试标记、证据来源分条自述；主线只核 transcript SHA-256 与侧通道工具执行次数 0。
- 摘要、失败、取消的用量累加到同一请求；provider 不返用量记 0，估算值不冒充实际用量。
- 问题 ≤4000 字符；`POST` 先 202 接纳、后台准备，SSE 每帧先发累计状态；无快照、配置变化、父会话忙、幂等 ID 冲突返 409，全局并发满返 429。

## 验证方法

- 语料：历史 19/20/21/50 组，第一组答案埋 `EARLY-DECISION-ALPHA`；断言 `info.RecentExchanges == min(n,20)`、`memory.Through == max(0, n-20)`、首轮决策仍在请求里、重启后摘要命中不多调。
- 预算回归：5500 行 `<script>` 拼出 >200000 字符快照，`BuildRequest` 必须成功，`MaxTokens == 8192` 且估算 <200000；快照 JSON 前后逐字节相等。
- 工具配对：`reflect.DeepEqual(final.Messages, llm.MessagesForAPI(final.Messages))` 为真，近期工具证据仍在。
- 调用次数：摘要调用落在 [2,12]；`calls == 12` 即上限终态。
- 计数口径：`context_test.go` 8 个测试函数、4 处表驱动 `t.Run` 展开成 15 个子用例（合计 19 个执行用例）、30 处 `t.Fatal`；`VALIDATION.md` 工程检查表 21 行。
- 跑法：`go test -race ./sidequestion ./db ./server -run 'TestSide|TestCheckpoint|TestSnapshot|TestBuildRequest|TestService|TestMainSide|TestTaskArchive' -count=1`。
- `validation-2026-09-10.json` 口径：`streaming.assertions` 6 条（3 条 `completed` 加 transcript、activity、`side_tool_executions_zero` 三条 `passed`）；`side_questions` 3 条 ordinal 4/5/6，16.97/7.24/7.74 秒；`restart.history_count=3`、`main_not_rerun=true`；`non_streaming.usage` input 11734、output 138、cache_read 11520；`stream_usage_probe` 12 帧 0 usage 帧（端点不给用量，0 不等于未计费）；`qwen_review.verdict=accept`、`concerns=[]`、prompt 6625 / completion 312 / total 6937。
- 红灯不计入通过项：`TestInheritedActivityDetailAndRelationDeletion`、`TestTaskMetadataPatchReturnsRenameAndPin` 在 `TempDir RemoveAll` 阶段失败，基线可复现。

## 失败模式与判据

- 答非所问：空文本无 tool call → 「模型没有返回回答」；流缺 `SEMessageStop` → 「模型响应中断，请重新提问」；摘要空、`stop` 为 `max_tokens`/`length`、带 tool call、估算 >2200 → 不写缓存、`Through` 不推进。
- 污染主线：判据是 transcript SHA-256 不变、侧通道工具执行 0 次、快照 JSON 前后相等；摘要请求必须 `len(Tools)==0`。
- 预算穿透：恢复只走一次（`attempt < 2`），前置是正文为空、无 tool call、`ctx.Err() == nil`；第二轮估算不降即报「旁路压缩未能进一步缩减上下文，已停止重试」；摘要 12 次报「整理已达到本次处理上限」。`isContextOverflow` 认 6 个标记：`context_length_exceeded`、`maximum context length`、`context window`、`prompt is too long`、`input is too long`、`context length exceeded`。
- 游标错乱：`ordinal` 非严格递增或状态非 `completed` → 「旁路历史游标无效」。
- 清空竞争：清理版本不匹配的迟到写入被条件更新挡掉。

## 与既有卡衔接

- 长会话压缩卡：预算三分法与 `messageGroups` 组边界可直接搬进任意 agent 的压缩实现。
- 多 agent 编排卡：`Parent.Key()` 三键命名是父子会话隔离的最小口径，派生 Worker 走 intent 维度而非执行槽位。
- 用量核算卡：摘要、失败、取消同账累加与缺用量记 0 是对账前提。
- 回归台账卡：validation json 四段结构（`assertions`/`side_questions`/`restart`/`non_streaming`）可当证据模板。
