# ai-infra-security

攻击面知识域 — **4993 个文件** / 7 个子目录

## 子目录
```
AI-Infra-Guard-Tencent
hardened-self-update
llm-key-pool-failover
mcp-http-sse-client
notify-channel-secret-masking
side-question-context-budget
```

## 融合亮点

- `AI-Infra-Guard-Tencent/` — 组件漏洞指纹库（按产品分目录的 YAML）
- `mcp-security/` · `hunt-mcp/` · `hunt-mcp-security/` — MCP 服务端与工具链攻击面
- `llm-key-pool-failover/` — 多 key 池健康打分、熔断退避、幂等安全窗
- `side-question-context-budget/` — 侧问题隔离与上下文预算裁剪
- `notify-channel-secret-masking/` — 通知渠道去密、SSRF 判据与签名
- `hardened-self-update/` — 源固定 + host 白名单 + 逐跳校验 + SHA256SUMS
- `mcp-http-sse-client/` — MCP Streamable HTTP/SSE 传输与 JSON-RPC 关联

---

@TGSEC社区 · @TGSEC-Qtzuu 整理

<!-- ingest-artex-20261105 -->
## 2026-11-05 增量（框架吸收）

- `llm-key-pool-failover` — 多 key 池健康打分、熔断退避与幂等安全窗
- `side-question-context-budget` — 侧问题隔离与上下文预算裁剪 + 断言语料口径
- `notify-channel-secret-masking` — 多渠道通知去密、SSRF 判据、签名与模板差异
- `hardened-self-update` — 硬化自升级：源固定、host 白名单、逐跳重定向校验、SHA256SUMS
- `mcp-http-sse-client` — MCP Streamable HTTP/SSE 传输、JSON-RPC 关联与重连
- `context-compaction-budget` — 长作业压缩闸门：输入/输出预算公式 + minor/major 两级阈值 + digest 签名复用 + 冷节点 R6/K2
