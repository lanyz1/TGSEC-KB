## 十六、修复建议（高级）

- **统一授权中间件**：对象级授权在数据访问层强制（`WHERE user_id = :current`），不在业务散落
- **间接引用**：用户侧用随机引用ID（UUID v4/不透明标识），服务端映射，杜绝自增ID外泄
- **JWT硬化**：仅RS256/ES256白名单算法、校验iss/aud/exp/jti、kid白名单+jku禁用、短TTL+refresh轮换
- **OAuth硬化**：强制PKCE、redirect_uri精确白名单（禁止前缀后缀模糊匹配）、state绑定session、scope最小化、refresh绑定client
- **网关纵深**：网关只做传输层，鉴权下沉到各服务；禁止信任X-Forwarded-User类头（除非网关签名）；路径归一化一致
- **BFF隔离**：BFF不替代服务鉴权，内部字段不可信
- **批量分配防护**：DTO白名单+禁用auto-bind+防御原型污染（Object.freeze/__proto__过滤）
- **速率限制**：IP+用户+Token+端点多维+分布式一致性计数
- **LLM/MCP硬化**：AI资产对象级授权（flow/thread/credential）、prompt注入防护（输入输出过滤、工具权限隔离）、MCP工具鉴权+最小权限、凭证不注入prompt上下文
- **Webhook硬化**：强签名（HMAC-SHA256恒定时间比较）、全字段验签、timestamp+nonce+重放窗口、密钥轮换管理
- **供应链**：第三方URL白名单+SSRF防护、SDK版本锁定与漏洞扫描、Webhook来源IP校验
- **错误处理/最小数据**：统一错误、仅返回必要字段、敏感数据脱敏
- **日志监控**：异常访问模式（ID遍历、跨租户请求、令牌滥用）告警

