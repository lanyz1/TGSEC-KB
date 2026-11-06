## 一、API攻击面与分类

### 1.1 API类型
| API类型 | 特征 | 协议/格式 |
|--------|------|---------|
| REST API | HTTP方法+JSON | GET/POST/PUT/DELETE/PATCH + JSON/XML |
| GraphQL | 单一端点/graphql | POST with {"query":"..."} |
| gRPC/Protobuf | HTTP/2 + protobuf | application/grpc二进制 |
| SOAP Web Service | WSDL/XML | application/soap+xml |
| WebSocket | ws://wss:// | 升级HTTP连接 |
| JSON-RPC/XML-RPC | RPC风格 | POST /rpc方法调用 |
| REST-like API | 自定义路径/方法 | 混合格式 |
| Webhook/回调 | 外部触发 | POST回调URL + 签名验证 |
| Web API v1/v2/v3 | 多版本API | /api/v1/xxx |
| **SSE (Server-Sent Events)** | 单向流式 | `text/event-stream`，EventSource |
| **BFF (Backend for Frontend)** | 面向客户端聚合 | /bff/、/mfe/、/edge/ 前缀，内部拼装多服务 |
| **事件驱动/异步API** | 消息队列/事件总线 | Kafka/EventBridge/Webhook订阅，AsyncAPI规范 |
| **MCP/Agent工具API** | LLM工具调用 | JSON-RPC over stdio/HTTP/SSE，`initialize`/`tools/call` |

### 1.2 OWASP API Top 10 (2023) 与高级对抗映射
1. **API1:2023 BOLA** → 自动化BOLA检测（4.4节）、LLM对象BOLA（第十二章）
2. **API2:2023 认证失效** → JWT算法混淆矩阵、OAuth授权码劫持、Token重放/Refresh滥用（第三章）
3. **API3:2023 BOPLA** → 批量分配+JSON深度合并（第四章）
4. **API4:2023 资源滥用** → 速率限制多维绕过、GraphQL成本攻击（第六章）
5. **API5:2023 BFLA** → 方法混淆、网关/版本降级绕过（第四章/第十一章）
6. **API6:2023 敏感业务流** → 业务流状态机滥用（第四章）
7. **API7:2023 SSRF** → 第三方API消费SSRF（第十三章）
8. **API8:2023 安全配置** → CORS/网关配置/调试端点（第七章/第十一章）
9. **API9:2023 资产管理** → 影子API/版本漂移（2.2节/7.3节）
10. **API10:2023 不安全消费** → 第三方API供应链、Webhook签名绕过（第十三章）

