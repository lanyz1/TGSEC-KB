---
name: tool-gate-approval-interception
description: "给 agent 加工具级审批门禁、危险命令拦截层时加载。PreToolUse/PostToolUse 双钩子挂点：规则落库按 priority 降序首命中短路，动作三档 allow/deny/ask；ask 落待审行等人工 decide，超时判定改不了人工决定；deny 回模型带平台管控语义，防 agent 把门禁当目标侧 WAF 去绕。含内置种子规则（rm -rf、DROP、FLUSHALL、删除接口路径、外联管道）、凭据读取只读放行的判据、trace 三态关联、AuditEntry 与 G5 归因计数。"
sources: art-content, operator_experience
---

## 定位

把「这次工具调用放不放行」拆成规则判定 → 无命中走模型兜底 → 判不准才转人工三段闸，每段判据都落成可复盘的行。门禁是策略，不是让 agent 去绕的障碍物。

## 双钩子挂点与执行顺序

装配面只有两个钩子，一次注册全会话共用：

```go
hook.NewRegistry().On(hook.PreToolUse, g.preToolUse).On(hook.PostToolUse, g.postToolUse)
```

`Hooks()` 交给 agent 会话；任务侧由引擎挂成 inner 钩子（`t.Guard.Hooks()`），后台 worker 与会话同一套。测试可直呼 `g.Hooks().PreToolUse(ctx, "Bash", input)`，拿三返回值：拦没拦、消息、错。

PreToolUse 四步不可换序：抽命令面（`Bash` 与 `shell_open` 取 `command` 字段，`shell_send` 取 `text` 字段，其余工具命令留空）→ 先 `record(tool, "allow", "", cmd)` 记一条放行（这一条早于判定，只证调用到场）→ `applyIntercept`（interceptor 为 nil 放行；`IsToolEnabled` 不中放行；`WithCall` 冻结审查快照；`Match`；无命中再 `Judge`）→ 分流：`deny` 记 `denied` 行并 block；`allow` 记 `allowed` 行再放行；`ask` 见 `ctx.Err() != nil` 直接 block 且不建行，否则 `HandleAsk` 为 false 就 block。

block 走 `hook.Result{Decision:"block", Message:...}`，Message 由 `systemBlockMessage` 定型为「平台管控·非目标防御」+ 原因 +「此操作被禁止」。措辞是必需件：裸原因读起来跟目标侧 403 一个味，渗透 agent 的本能是改命令、换 payload 再打；写明平台身份，它才换路子。

PostToolUse 只归因不判定：仅 `Bash` 参与，分 `ok` / `blocked` / `error`，`blocked` 用 `(?i)\b(403|forbidden|waf|blocked|rate.?limit|429|captcha|denied)\b` 且先于 error 判。

## 规则模型

规则存表 `intercept_rules`，字段 `id、name、enabled、priority、match_target、match_type、pattern、action、message、timeout_enabled、timeout_seconds、timeout_action、created_at、updated_at`。加载 `ORDER BY priority DESC, id`，内存里是预编译的 `compiledRule`，坏正则 `continue` 跳过而不崩服；`Match` 逐条试、**首命中即返回**——短路的代价是低档 allow 救不回已被高档吃掉的调用。

取值域三处封闭：`match_target` 只认 `tool_name` 与 `tool_input`；`match_type` 只认 `string`（子串 `Contains`）与 `regex`；`action` 只认 `allow` / `deny` / `ask`，越界在 `validateInterceptRuleReq` 被打回 400，运行期没有第四种。

`tool_input` 的匹配对象是**整段 arguments JSON**，不是某个 command 字段：`Write` / `Edit` 正文、脚本源码、报告里的示例文本全在匹配面内。

缓存只有 `Invalidate()` 一个失效口，HTTP 侧 CRUD 自动调；自写调用方漏调就继续吃旧规则。工具集是 settings 键 `intercept_enabled_tools`（JSON 数组），缺省 `Bash、WebFetch、web_search、shell_open、shell_send、Write、Edit、MultiEdit`；不在集合里的工具连兜底都不进，这是「漏放」第一嫌疑。

内置规则种三批，各带幂等旗标 `intercept_default_rules_v1/v2/v3 = done`，用户删改重启不复活；全部是普通 `[内置]` 行，与自定义同权。优先级分层 `100` 系统破坏、`90` 数据库与缓存、`80` HTTP 破坏与删除接口；行默认 `timeout_enabled=false、timeout_seconds=60、timeout_action='deny'`。

模型兜底开关：`llm_judge_enabled`、`llm_judge_profile_id`、`llm_judge_prompt`、`llm_judge_timeout_seconds`（15）、`llm_judge_fail_action`（allow）、`llm_judge_ask_timeout_seconds`（300）、`llm_judge_ask_timeout_action`（deny）。判定只收一个 JSON 对象、恰好两键 `decision` 与 `comment`，重复键、额外键、多对象、尾随散文一律不可解析；`comment` 三段逐段非空，字面定界为：

```text
实际操作：〈一句话〉；成功后的后果：〈一句话〉；命中规则：〈策略编号〉
```

不可解析或模型报错走 `fail_action`。模型判定 `rule_id` 落 NULL，消息加 `[模型]` 前缀，`decision_source` 派生成 `rule` / `model` / `unknown`。

## 审批请求与人工回路

`HandleAsk` 的顺序就是生命周期：`auditFor(...,"pending")` → `CreateInterceptPending`（`rule_id=0` 是兜底行，`conversation_id=0` 存 NULL 表示后台任务，`task_id=""` 存 NULL）→ `bindResult` 绑定结果回调 → `pending.add(id)` 后**立刻重读 DB**（轮询端会在 INSERT 提交后、channel 注册前落决定，这次重读把它捞回来）→ 写 `intercept_request` activity（会话 `AppendConvActivity`，后台 `taskEmit` 打进探索流）→ 阻塞。

三个出口：人工决定唤醒；超时（`timeout_enabled=false` 无超时一直等；`true` 时 `timeout_seconds<=0` 兜底 60s，按 `timeout_action` 收，`status="timeout"`，理由「审批超时，按超时策略处理」）；`ctx.Done()` 落 `denied` + `CompleteIntercept("not_executed","执行前工作已取消")`。

人工侧：`POST /api/intercept/pending/{id}/decide`，body `{"decision":"allowed"|"denied"}`，其它取值 400；`GET /api/intercept/pending` 只列 `pending`；`GET /api/intercept/history?status=&decision_source=`；`GET /api/intercept/history/{id}` 带 `audit`；`GET /api/intercept/task/{taskID}`。`Decide` 落到 `ResolveIntercept(status=allowed|denied, action, "人工允许执行"/"人工拒绝执行")` 再 `pending.resolve` 唤醒；已处理的行影响行数为 0，返回 `ErrAlreadyDecided`，HTTP 映射 409。

会话级暂停等价于 ctx 取消，两处收口：ask 分支见 `ctx.Err()` 不建行直接 block（免孤儿行，也让 execOne 快结束）；已进 `HandleAsk` 被取消的落 denied + `not_executed`。后台任务照样建行，审批页与侧边栏徽标亮，worker 老实阻塞在 channel 上等人来点。

超时改不了人工历史：UPDATE 带 `WHERE id=$1 AND status='pending'`，影响行数为 1 才算收口；为 0 就 `GetInterceptDetail` 重读真实状态。

## 判定链留痕 trace

`WithTrace(ctx, user, prior)` 抓三样：原样用户消息（32KiB）、`prior` 上下文（每条 8KiB、只留最近 24 条）、工具事件进出（输出 64KiB），全部按 rune 安全截断并置 `truncated`。

`Start(id, tool, input)` 落一条 `InterceptAudit`：`run_id`、`tool_use_id`、`correlation`、`input_digest`（JSON 规范化后 sha256）、`user_message`、`captured_at`、`context` 快照。`WithCall` 在模型判定开始前抢占，按 `tool + input_digest` 找未 claim 的候选：唯一 → `exact` 并锁死快照；多候选 → `ambiguous` 且全部标脏永不洗白、`tool_use_id` 留空；无 trace → `unavailable`。两个同输入调用并行时宁记 ambiguous，不按先后硬凑身份。

`Complete` 出 `succeeded` / `failed`；`Finish()` 把没等到结果的记 `unknown` +「执行结束但未收到工具结果」——被打断与报错是两件事，缺结果不写成功。写库走双键 `run_id + tool_use_id`，且要求该行 `effective_action='allow'`、`execution_status='awaiting_result'`，被拦的调用不会被写成执行失败。

保留分档决定复盘能看什么：`allowed` 抹掉 `user_message` 与 `context`（每调用一行，24×8KiB 会灌爆表），但 `model_input` / `model_input_digest` 全留，含自动放行；`denied` 与 `pending` 留全量。误判复盘吃的就是这一档。

## 审计日志与失败归因

`AuditEntry` 是最粗一档在场证明：`ts`（Unix 秒）、`tool`、`action`（`allow` / `block`）、`reason`、`command`；环形缓冲 2000 条丢最旧；`GET /api/audit?task={taskID}` 一次返回 `{entries, attributions}`。

`attrib` 三键 `ok` / `blocked` / `error`，只统计 `Bash`，`blocked` 先于 `error`：返回体出现 403 / WAF / rate limit 即算目标侧阻拦，planner 据此换策略而不是在同一个 WAF 前反复送。

两层别混：`AuditEntry` 是工具面（命令原文、放还是拦），`intercept_pending.audit` 是判定面（规则名、初始动作与理由、输入摘要、模型输入与配置摘要、超时生效、最终动作、执行状态、输出截断标记、`execution_ended_at`）。

## 规则写法样例

全为 `match_target=tool_input`、`match_type=regex`、`action=deny`、`timeout_enabled=false`：

| 名称 | priority | pattern | 判据 |
| --- | --- | --- | --- |
| `[内置] 递归强制删除 rm -rf` | 100 | `(?i)\brm\b.{0,80}(?:-[a-z]*r[a-z]*f[a-z]*\|-[a-z]*f[a-z]*r[a-z]*\|--recursive\|--no-preserve-root)` | 80 字符窗内同时出现递归与强制；`rm -r`、`rm -f` 单用不中 |
| `[内置] SQL DROP DATABASE / TABLE / SCHEMA` | 90 | `(?i)\bDROP\s+(?:DATABASE\|TABLE\|SCHEMA\|INDEX\|VIEW\|TABLESPACE\|USER\|ROLE)\b` | 只认 DDL 对象关键字 |
| `[内置] Redis FLUSHALL / FLUSHDB` | 90 | `(?i)\b(?:FLUSHALL\|FLUSHDB)\b` | 缓存全清不可逆 |
| `[内置] 删除类接口路径` | 80 | `(?i)/(?:(?:delete\|remove\|unlink\|erase\|destroy)[-\w]*\|del)(?:[/?#"'\s]\|$)` | 动词后必须有分隔符：`/delivery`、`/details`、`/delta` 不中，`/deleteAll`、`/delete_user` 中；不分 HTTP 方法，多数应用 GET/POST 就能触发删除 |
| `[内置] 数据外泄管道` | 80 | `(?i)(curl\|wget\|nc\|ncat)\b[^\|]*\b(\|\s*(curl\|wget\|nc))` | 种子里 `enabled=false`：管道形态在反连与搬数据上误杀高，要外联管控就手动开 |

刻意不写成规则的两类：凭据读取（`/etc/shadow`、`.env`、`--dump` 属只读，读到敏感信息本身不是拦截理由，拦截点放写与不可逆）；批量写（种子库无此条，数量阈值交兜底按影响面归 ASK，正则数不清并发）。要加就走 `CreateInterceptRule(name, matchTarget, matchType, pattern, action, message, priority, enabled, timeoutEnabled, timeoutSeconds, timeoutAction)` 或 `POST /api/intercept/rules`，写完 `Invalidate()`。

## 误杀排查顺序

1. 看 `GET /api/intercept/history/{id}` 的 `audit.rule_name` 与 `decision_source`：`rule` 是规则命中，模型没参与；`model` 才是兜底。
2. 规则命中就对 `tool_input` 原 JSON 跑同一 pattern。整段 arguments 都在面内，`Write` 正文写了 `rm -rf` 示例、脚本注释留 `curl -X DELETE`，照样拦。
3. 看优先级：高档先中即短路。要放行就抬 allow 规则的 priority，别去改低档 pattern；同档则收窄 pattern。
4. 工具不在 `intercept_enabled_tools` 里，整层不生效；兜底另由 `llm_judge_enabled` 管，两把开关逐个核。
5. 规则列着却不生效：`loadLocked` 把编译失败的正则静默跳过，比对 `pattern` 与 `POST /api/intercept/rules` 的 400 结果。
6. 编码变形是漏放第二来源：`r''m -rf`、base64 后 `eval`、变量拼接、分段重定向都不在正则面内；只能靠兜底，或把规则抬到 `tool_name` 层对整类工具要审批。
7. `ask` 泛滥把审批台淹掉：把该规则收成 `deny`，或把 pattern 收到只覆盖不可逆动作。ASK 的语义是参数不足以判归属，不是看着危险。
8. 改完规则或工具集必须 `Invalidate()`；兜底配置是每次现读，不用等失效。

## 与既有卡衔接

- 上层执行卡（红队假设驱动、活体渗透执行）负责打哪、怎么打；本卡是出口闸，只决定某个动作在这一层过不过，不改攻击面方法。
- 手法卡的 payload 撞 `deny`（删订单、改余额、`DROP`、删接口路径）时，按上面第 2、6 步定位是规则还是兜底，再换动作形态；被拦不是目标防御，重试同一字符串没有收益。
- 留痕与证据卡可与 `intercept_pending.audit` 对账：`input_digest` 对同一 tool_input 是稳定 sha256，`run_id + tool_use_id` 是唯一双键，跨表核对不会串行。
