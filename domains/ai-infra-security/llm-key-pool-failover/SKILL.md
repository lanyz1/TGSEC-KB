---
name: llm-key-pool-failover
description: "跑长任务时多 API key、多供应商（anthropic/openai 混排）要自动轮换、额度打满要立刻换供应商、429/5xx 要退避、连续失败要熔断冷却、按会话粘性路由要命中同一后端时加载。给成员链模型（Rank 权重、同权轮转、窗口预筛、全进程共享限流）、健康度计分（瞬时 3 次软熔断、401/402/403/404 一次硬熔断、1m/5m/30m 冷却梯度、成功清零的半开探测）、选路顺序、429 改判 402 的传输层钩子、错误分类与安全窗幂等边界、用量口径、复盘指标与失败模式判据。"
sources: art-content, operator_experience
---

# LLM Key 池与故障转移

## 定位

N 个 LLM 配置排成有序链，请求按链序下发；成员在"尚未向调用方交付任何输出"的安全窗内失败即切下一成员，切流与冷却由进程级熔断表统一裁决。

## 池模型

`Member{ID, Name, Model, Format, Priority, Active, Rank, WindowTokens int, Prov}`。`ID` 即 llm_profiles.id，健康状态按它索引；`Priority`、`Active` 只做展示，排序键是 `Rank`（大者先）。

权重：活动/绑定配置的 `Rank` 抬到 `RankActive = int(^uint(0)>>1) - 1`，其余按 priority 降序；同 `Rank` 成组，组内每次把起点后移一位轮转（`Pool.rr` 是 `atomic.Uint64`，入参 `n = rr.Add(1)-1`），重复 key 轮流打头；链头独占 Rank，不入组。

并发：池不设每成员闸门。成员构造后不可变，可变状态只在 `Registry` 的一把 `sync.Mutex` 内；节流落在 provider 实例的 `llm.RateLimit{PerSecond, PerMinute}`（0 = 不限），planner、全部 worker、主 agent 共用一个 limiter。

粘性会话：`Config.SessionHeaderKey` 非空时每请求带一个自定义头，头名操作者配、头值取当前会话 id（`conv-<id>`、`exp<x>-worker-i<intent>`），经 `transcript.WithSessionID` 挂 context、`quotaAwareTransport.RoundTrip` 读出填头；按 session 做提示缓存与粘性路由的网关靠它锁后端。

空链 `New` 返回 nil 退回裸 provider；单成员链等同裸 provider；全链走空返回包装 `ErrExhausted` 的错误。

## 健康度与打分

`State{Fails, Trips, OpenUntil, LastError, LastAt}`，`Open()` 判 `now < OpenUntil`；`Trips` 兼作冷却梯度下标，`LastError` 裁到 300 字。

成功 `Pass(id)` 删整条状态（不衰减、删除重建）并回调 `forget(id)`；失败 `Trip(id, msg, hard)` 只做 `Fails++`。没有成功率滑窗、没有延迟加权——延迟只在 `TestConnection` 往返计时（30s 超时）与 capture 时间戳里，按延迟切流得自己用 attempts 另算。

半开探测隐式：开闸时 `Fails` 归零（已计入本次 trip），冷却到期 `Open()` 转 false、成员重回 `order()`；探测失败从 1 重计，成功走 `Pass`。

额度耗尽一步到位：`isHardFailure` 对 401/402/403/404 返 true，`Trip` 见 hard 立即 `Trips++` 写 `OpenUntil`；无状态码的传输失败（`statusOf` 得 0）归瞬时，攒够阈值才熔断。

## 选路顺序与熔断

`order(req)` 三步：`estimateTokens` 粗估体量（system 各段 + 消息块递归 + 每工具 `len(Name)+len(Description)+属性数*120`，最后 `*2/7` ≈ 3.5 字符/token、故意偏高），`WindowTokens > 0 且 est > WindowTokens` 跳过（省一次注定 400 的往返）；`IsOpen` 为真跳过；余下按 Rank 分组轮转；全被滤光返回 `members[:1]` 硬探链头。

换 key 与换供应商同一动作：走链上下一成员。`Format` 不参与决策，只看 Rank 与健康度；熔断粒度是 profile（`Member.ID`），无供应商级熔断器；同一 base 整段失效时链落到另一 Format，表现为连续多行同前缀成员开闸。

阈值：瞬时 3 次（`softTripAfter = 3`），`SetPolicy(softTrip, cooldown)` 可改——`>0` 用该值、`=0` 默认、`<0` 瞬时永不熔断只剩硬失败；硬失败 1 次。冷却 `backoff = {1m, 5m, 30m}` 按 trip 次数取档、末档重复；`cooldown > 0` 改固定窗（如 90s）且不再升级。`Restore` 回灌、`Reset` 立即恢复、`Snapshot()` 供状态接口。

## 退避与重试

四层：SDK 建连 `ConnectAttempts/ConnectInterval`（映射 `MaxRetries`/`RetryInterval`）默认 3 次、0.5s 起指数封顶 8s，覆盖重置/超时/429/5xx 且都在流开始前；SDK 空响应 `EmptyAttempts/EmptyInterval` 默认 2 次、同梯度、仅 openai 格式；同 provider 安全窗 `StreamAttempts/StreamInterval` 默认 2 次、0.5s 起封顶 4s，由 server 侧消费；最后是池级换成员。次数 0 = 默认、负 = 关层、>0 = 该值；间隔 0 = 原指数、>0 = 固定。状态码从 SDK 错误串按 `statusRe = status (\d{3})` 抠：

| 分类 | 判据 | 动作 |
|---|---|---|
| 429 | status 429 | 换成员，瞬时，攒 3 次熔断 |
| 5xx | status ≥ 500 | 换成员，瞬时 |
| 网络 | 抠不到状态码（reset/DNS/超时） | 换成员，瞬时 |
| 402 | status 402，或 429 正文命中额度标记后被改写 | 换成员，立即硬熔断 |
| 401/403/404 | 同左 | 换成员，立即硬熔断 |
| 400 | status 400 | 不换，原样上抛 |
| 其他 4xx | 405/409/422 兜底 false | 不换，不写健康记录 |
| 取消/超时 | `ctx.Err() != nil` 或 `context.Canceled/DeadlineExceeded` | 不换，不算 LLM 故障 |
| 200 空正文 | openai 格式零 content block | 交空响应重试，`TestConnection` 判失败 |

内容拒绝不单列：拒绝性 400 不换成员，200 带正文的软拒绝按成功记 `Pass`。

幂等边界是唯一硬规则：`Stream` 里成员只能在尚未 yield 任何事件时被放弃（`emitted` 标志）；文本或 tool_use 一旦触达调用方，中途失败原样上抛交给会话恢复——换模型重放会重复 assistant 轮次、污染历史。401/402/429/5xx 全在建连期、正文未读之前，天然在安全窗内；`Complete` 原子、无部分输出，逐成员重试无副作用。差异：`Stream` 的非转移错误直接上抛不写健康记录，`Complete` 同路径记一次 `Pass`。

## 配额与成本

capture 口径：`quotaAwareTransport.RoundTrip` 记请求体快照（`SetRequest(requestBodySnapshot)`，走 `GetBody` 复制、不消费）与响应（`TeeResponse`，200 的 SSE 继续流），`Attempts()` 给逐次 HTTP status 与 body，日志 `clipBody` 裁 4096 字节。一次业务请求 = N 次 attempt，成员用量按 attempt 的 status 归属，按调用次数算会漏掉被跳过的成员。

限额触发点只一处：`IsQuotaExhaustedMessage` 在 429 正文找余额/账单标记（`insufficient_quota`、`billing_hard_limit_reached`、`credit balance`、`insufficient balance`、`payment required`、`status 402`、余额不足、额度已用尽、欠费），命中即改写 402 让池立刻硬熔断。三条排除先跑：含 401/403/5xx 状态串不认；含 `rpm`/`tpm`/`rpd`/`qps`、`quota_metric`、`rate_limit`、`too many requests` 等瞬时限流词不认；`resource_exhausted` 须不带 `rate limit`、`too many requests`。改判在 tee 之后，capture 存原始 429、池见 402。

成本闸门另两处：`MaxTokens`（随请求发）与 `MaxTokensField`（openai 侧 `max_tokens` 对 `max_completion_tokens`，推理模型只认后者）；`ContextWindowK` 不发服务端，只本地算 `CompactionWindow()`：0 → 200K，夹到 [32K, 1000K]。

## 观测

必落三类日志：转移一行 `LLM 故障转移：A → B，原因：<300 字内>`、开闸一行 `已熔断`、耗尽一行 `轮询链已耗尽(N 个配置全部失败)`。`Snapshot()` 的五元组足够回答"为什么被跳过"；attempts 的 status 与 body 配 `TestConnection` 延迟区分"200 空正文"与"真限流"；`SessionHeaderKey` 头值当键把切流挂回会话。反指标：`Trips` 涨而 `Fails` 在 0~2 打转 = 反复软熔断；`Trips` 涨而 `Fails` 恒 1、`LastError` 不变 = 一直硬失败，该修 key。

## 失败模式与判据

- 全链同 key：`Trips` 逐个涨、耗尽刷屏，attempts 的 body 字节级相同。
- 瞬时限流误判成余额耗尽：退避期间突然大量开闸，漏了该网关措辞的排除项。
- 冷却过长掩盖恢复：`OpenUntil - LastAt` 恰 30m，钉小 `cooldown` 可治。
- 窗口误杀：长 system 加多工具的活只剩超大窗口成员在干，比对 est 与 `WindowTokens`。
- 中途断流：`emitted` 置位只能上抛，该轮终止不换 key，续跑靠会话 resume。
- 空链静默：`New` 返回 nil 后全部落裸 provider，链配了却从不切换，查成员数 0 或 1。
- 取消计成故障：终止归因错、备用 key 白烧，查 `shouldFailover` 首个 `ctx.Err()` 分支。

## 与既有卡衔接

压缩阈值与上下文预算接 `side-question-context-budget`，窗口夹取算法在那，别在 `WindowTokens` 上重做；`Config.Proxy` 直连语义（留空不回退环境变量、只认 http/https/socks5）接 `v2rayn-proxy-diagnostics`；网关 429/5xx 是限流还是拦截在 `waf-block-layer-triage` 判；整库检索用 `tgsec-arsenal-router`。
