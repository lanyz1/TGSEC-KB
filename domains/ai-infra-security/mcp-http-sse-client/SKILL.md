---
name: mcp-http-sse-client
description: "要接 MCP 服务器的 HTTP/SSE 传输、做 JSON-RPC 关联与重连、处理流式事件与超时、排查握手失败或会话失效时加载。给两条传输形态：单端点 POST 帧与事件流双答、legacy 端点公告与会话标识、会话头的捕获与 DELETE 收尾；给自增 id 配对、pending 表按 id 分发、多行 data 串接与 8MB 单行上限、心跳注释行不触发分帧、120s 超时与 1s 关流、三层错误面逐层判据、串行锁与断线单槽、七条失败模式。"
sources: art-content, operator_experience
---

## 定位

把一个远端 MCP 服务器收敛成一条可审计的 JSON-RPC 通道：一个 URL 进，工具表与调用结果出，两条传输共用一套 ID 关联与三层错误判据。

## 传输形态

`New(ctx, server, url, headers, insecure)` 走 Streamable HTTP：同一个 URL 既接 POST（JSON-RPC 帧）又接 DELETE（会话收尾）。每帧固定三件头：`Content-Type: application/json`、`Accept: application/json, text/event-stream`、`MCP-Protocol-Version: 2025-06-18`（`protocolVersion` 常量，legacy 侧用 `2024-11-05`）。响应头带 `Mcp-Session-Id` 且本地 `sessionID` 为空时（initialize 那一跳）落库，之后每帧回带 `Mcp-Session-Id`。按响应 `Content-Type` 是否前缀 `text/event-stream` 分流：命中交 `parseSSE`，否则 `json.NewDecoder` 直解一个 `rpcResponse`；响应只在该 POST 的 body 里找，不跨连接。

`NewSSE(ctx, server, sseURL, headers, insecure)` 走 legacy：先长连 `GET <sseURL>` 带 `Accept: text/event-stream`，`readSSEEndpoint` 逐行扫到第一条非空 `data:` 行当端点公告（形态 `event: endpoint` + `data: <scheme>://host/message?sessionId=<id>`），相对地址用 `url.Parse(base).ResolveReference` 补全成 `messageURL`；此后所有 POST 打这里、`Accept: application/json`，会话靠 query 的 `sessionId`，与 `sessionID` 字段无关。

握手都在构造函数里走完：`initialize`（`protocolVersion` 取 `c.protocol`、`capabilities` 空对象、`clientInfo` 固定 `{name, version}`）紧跟 `notifications/initialized`。legacy 的 initialize 失败先 `Close` 再返错，不留悬挂协程。

## JSON-RPC 关联

`rpcRequest{JSONRPC, ID int, Method, Params}` 与 `rpcResponse{JSONRPC, ID int, Result json.RawMessage, Error *rpcError}`。ID 是 `c.mu` 内 `c.nextID++`，从 1 起；`id` 带 `omitempty`，于是通知帧（`notify`）根本没有 id，POST 回 `202 Accepted` 空体，`roundTrip(expectResp=false)` 返 `nil, nil`。

Streamable HTTP 是"一跳一配"：`call` 取 id → `roundTrip` → 命中流式则 `parseSSE(body, body.ID)`，id 不等于 `wantID` 的帧一律丢弃（服务端下发请求/通知、或混入上一跳残留响应时靠这条过滤）。没有全局 pending 表，也就没有乱序——每跳独占自己的响应体。

legacy 反过来：`pending map[int]chan *rpcResponse` 在 POST 之前登记（chan 容量 1），读协程 `readLegacySSE` 按 `response.ID` 取出、先 `delete` 再投递；清理靠 `defer delete`，成功与 ctx 取消都摘表，超时只由 `select` 里的 `<-ctx.Done()` 分支收口，迟到响应无人接手即丢。

并发：两把锁分工。`c.mu` 只护 `nextID`/`sessionID`；legacy 的 `legacyMu` 把 `legacyRoundTrip` 整段串行，同一时刻只有一跳在飞，多 goroutine 调 `Call` 排队而非并行。Streamable HTTP 无这层串行。

## SSE 解析

`parseSSE(r, wantID)` 只认两类行：`data:` 与空行。空行是事件边界，触发 `flush`：`dataBuf` 非空就整段 `json.Unmarshal` 成 `rpcResponse`，解析失败静默跳过，id 不匹配也静默跳过，匹配即返回首帧。

多行 `data:` 是"逐行 `TrimSpace` 后直接串接"，不插换行、不做 `\n` 还原。拆点落在令牌边界时串接串仍是合法 JSON；拆点落在令牌中间则整帧解析失败被丢。

`event:`、`id:`、`retry:` 三类字段完全不被读取；以 `:` 起头的心跳注释行不命中 `data:` 前缀，当噪声跳过，且不结束事件——长静默期由 `http.Client.Timeout` 或 ctx 兜底，不靠心跳计数。

读缓冲：`bufio.Scanner` 配 `sc.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)`，单行上限 8MB，超限得 `bufio.Scanner: token too long`，经 `sc.Err()` 上抛；流结束仍无匹配帧给 `mcp: no matching response in event stream`。

legacy 读协程更糙：`bufio.Reader.ReadString('\n')` 逐行读，只挑 `data:`，`json.Unmarshal` 失败或 `ID == 0` 的帧丢弃；读错误在非 `context.Canceled` 时塞进容量 1 的 `streamErr`（`select/default`，满则丢）。`streamDone` 在协程退出时关闭。

## 重连与恢复

客户端不带重试、不带退避、不带 Last-Event-ID 续传：`New`/`NewSSE` 各只 initialize 一次，任何一跳失败原样上抛，恢复动作在调用方——重建 Client 等于新会话、`nextID` 从 1 重发。

超时值只有两处：Streamable HTTP 的 `&http.Client{Timeout: 120 * time.Second}` 覆盖建连到读完 body；legacy 的 `&http.Client{}` 零超时（长连故意不设），单跳上限交给 ctx；`Close` 等 `streamDone` 最多 `time.After(1 * time.Second)`。

session 失效按信号分档：POST 非 2xx 得 `mcp http <code>: <正文前 2048 字节>`；legacy 两条腿（GET /sse、POST /message）得 `mcp sse http <code>: <片段>`。任一非 2xx 都没有重试、没有重新 initialize 的兜底，`Mcp-Session-Id`/`sessionId` 被服务端丢弃后唯一出路是重建 Client；`mcp sse endpoint: <err>` 说明端点公告没来或流提前关；`mcp sse stream: <err>` 来自 `streamErr` 单槽，被某跳取走后后续跳只能在 `ctx.Done()` 上耗到截止。

幂等边界：`tools/call` 重发即重放，客户端不做去重、不复用 ID 查重，`nextID` 只增不减。带副作用的工具（写盘、外发请求、改配置）重连后靠工具侧幂等键；`tools/list` 与 initialize 天然可重放。

## 错误面

三层分开判，别混成一句"调用失败"：

1. 传输层：非 2xx → `mcp http <code>` / `mcp sse http <code>`，body 只留前 2048 字节（`readSnippet` + `io.LimitReader`），够看清网关或鉴权回的 JSON/HTML。
2. JSON-RPC 层：2xx 但 `resp.Error != nil` → `*rpcError{Code, Message}`，`Error()` 为 `mcp rpc error <code>: <message>`。这一层是"方法被认下但被拒"，与状态码无关。另两条空/畸形判据：`call` 收 nil 得 `mcp: empty response for <method>`；解码失败得 `mcp: decode json response: <err>`。
3. 工具层：`tools/call` 结果里的 `content[]` 与 `isError`。`Call` 见 `isError: true` 返文本加 `mcp tool "<name>" error: <文本>`；`wrap` 出的 CoreTool 把 RPC 错误折成 `actool.Errorf("Error: " + err)`，把 `isError` 原样透传成 `actool.Result.IsError`，解码失败文案 `Error: bad MCP response: <err>`。

## 客户端实现要点

头 hygiene：构造函数对 headers 做一次 key 清洗——`strings.TrimSpace` 后判空、判 `\r\n`，命中直接 `invalid HTTP header name %q`；测试里 `"Authorization "` 这种带尾空格仍能配成 Bearer。这批头在 GET /sse、每次 POST、Close 的 DELETE 上重放。

ctx 传播：每跳 `http.NewRequestWithContext(ctx, ...)`，取消即断 body；legacy 的流用 `context.WithCancel(context.Background())` 独立生命周期，只由 `Close()` 取消，调用方 ctx 到期只杀单跳、不杀流。

`insecure` 为真时整个 `http.Transport` 被替换成零值加 `InsecureSkipVerify`：`Proxy` 归零（环境变量代理不再生效）、不自动试 HTTP/2。

并发安全：`nextID`/`sessionID` 走 `c.mu`，pending 表走 `pendingMu`，legacy 串行走 `legacyMu`，三把锁不重叠。

输出侧：`wrap` 的工具名走 `ToolName(server, name)` 得 `mcp__<server>__<tool>`，`inputSchema` 为 nil 时补 `{"type":"object"}`，权限回调固定 `permission.AskUser("call MCP tool <full>?")`；结果过 `actool.Capture(tc, text)` 按 `MaxOutputChars`（默认 30000）截断或溢写。`Call` 这条程序化路径绕开 AskUser，直接把 `content[]` 文本拼成字符串。

## 失败模式与判据

- 握手空转：`initialize` 返回 200 但流式端点要求 `Accept` 带 `text/event-stream`，先查请求头是否被中间层改写。
- 首帧即错：`parseSSE` 静默丢弃不匹配帧，流里只有一条错误帧时最终报 `no matching response in event stream`；把前几帧 dump 出来才见真实原因。
- 多行 data 断令牌：报解码失败或整体 no matching，比对服务端是否把 JSON 拆在令牌中间。
- legacy 吞吐恒 1：并发压测上不去，`legacyMu` 是瓶颈，换 Streamable HTTP 端点才有并行。
- streamErr 单槽耗尽：一次断线被某跳吃掉，后续跳全等到 ctx 截止；判据是"第一跳秒失败、后面全等 deadline"。
- Close 遗留：`sessionID` 为空时 Close 直接返回、不发 DELETE，服务端那侧的会话收尾没人做。
- 大结果灌上下文：未配 `ToolOutputDir` 时 `Capture` 只截断不落盘，全量结果随流丢弃。

## 与既有卡衔接

工具投毒与描述注入的攻面在 `mcp-security`，狩猎流程在 `hunt-mcp`，源码级找点在 `hunt-mcp-security`；本卡只管线怎么通、帧怎么配、错误怎么分层。上下文预算与截断阈值接 `side-question-context-budget`；MCP 后端挂在 LLM 网关后、429/5xx 要改判时接 `llm-key-pool-failover`；整库检索用 `tgsec-arsenal-router`。
