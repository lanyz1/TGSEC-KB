## 十五、API安全测试清单（高级版）

- [ ] API端点枚举（Swagger/OpenAPI/GraphQL/gRPC/Actuator/BFF/网关）
- [ ] 影子API/版本漂移（v1/v2对比、staging子域、未注销端点）
- [ ] 认证方式识别（JWT/OAuth/API Key/Basic/Cookie/mTLS/HMAC）
- [ ] JWT全矩阵：alg=none/弱密钥/RS256→HS256/kid路径遍历/jku/x5u/密钥类型混淆/claims篡改/refresh滥用
- [ ] OAuth深度：redirect_uri绕过变体/PKCE缺失/state缺失/scope提权/token混淆/IdP混淆
- [ ] API Key泄露（JS/APK/小程序/GitHub/env）+签名机制绕过
- [ ] BOLA：ID变形/关系链/多租户头/数组批量/分页绕过
- [ ] BFLA：方法混淆/版本降级/网关vs后端差异
- [ ] BOPLA批量分配（含__proto__原型污染、嵌套对象、PATCH差异）
- [ ] 自动化BOLA检测（Autorize+AuthMatrix+AutoRepeater多账户diff）
- [ ] GraphQL：introspection/成本深度/fragment/别名批量/持久化查询/指令滥用
- [ ] 注入：SQL/NoSQL（$ne/$gt/$where/$regex）/命令/JSON解析差异
- [ ] 速率限制绕过：头轮换/路径变体/HTTP2/批量数组/异步接口
- [ ] CORS反射+Credentials/前缀后缀绕过/CORS+CSRF组合
- [ ] 缓存投毒/敏感API缓存泄露（Cache-Control缺失/Vary缺失）
- [ ] WebSocket CSWSH/子协议/越权消息/Token位置
- [ ] gRPC反射/Protobuf逆向/网关双入口差异
- [ ] API网关绕过：路径归一化/身份头伪造/直连后端/服务网格
- [ ] BFF聚合层越权/内部字段篡改/SSRF代理
- [ ] LLM平台BOLA（flow/thread/knowledge跨租户）+MCP工具滥用+提示注入
- [ ] Webhook签名绕过（移除/篡改/重放/弱密钥/参数走私）+事件注入
- [ ] Actuator/debug/pprof/heapdump凭据提取
- [ ] 业务流状态机滥用（0元/无限领取/重复退款）

