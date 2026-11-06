## 十二、LLM/AI API与MCP攻击面（新增·前沿）

### 12.1 LLM平台BOLA（跨租户IDOR）
```
# AI平台（Langflow/Dify/Flowise/Chainlit等）对象：
# - Flow/Agent/Pipeline/Thread/Chat/Knowledge Base/Vector Store
# 攻击手法：
GET /api/v1/flows/{id}          # 枚举他人flow（CVE-2026-55255 Langflow）
GET /api/v1/threads/{id}        # 他人对话（Chainlit CVE-2025-68492）
GET /api/v1/knowledge/{id}/documents
# 跨租户：用租户A的token读租户B的flow/credentials
# 恶意执行他人flow → 窃取其内嵌LLM API Key/云凭证（T1552）
# 通过prompt注入让LLM输出内嵌secret："leak api keys"
# 案例：Langflow IDOR被用于枚举他人workflow并窃取credential context

# 重点对象：AI平台中"绑定凭证的资产"（flow/agent/集成配置）
# 攻击者真正目标是credential context，而非代码本身
```

### 12.2 提示注入与API滥用
```
# 直接/间接提示注入 → 绕过LLM输出策略
# 通过API参数注入：user input → prompt拼接
# 通过外部数据注入：RAG文档/网页抓取内容注入
# 越狱让LLM执行管理工具/访问受限数据
# LLM输出敏感信息（训练数据/系统提示泄露）
```

### 12.3 MCP（Model Context Protocol）攻击面
```
# MCP服务器暴露的工具列表：
POST /mcp  {"jsonrpc":"2.0","method":"tools/list","id":1}
# 调用工具（tools/call）→ 文件读写/命令执行/网络请求
# 若MCP未做鉴权/授权 → 任意工具调用
# 工具参数注入 → 越权操作（如删除文件、转账）
# MCP-Over-HTTPS/SSE的令牌管理缺陷
# Agent自主调用链：LLM被诱导调用敏感工具
```

### 12.4 AI代理凭证上下文窃取
```
# Agent平台常把API Key/令牌注入prompt上下文
# 间接注入（网页/文档内容）诱导Agent输出令牌
# 工具调用链滥用：Agent拥有的工具权限=调用者的权限上界
# 测试：构造文档触发Agent调用工具读文件 → 令牌泄露
```

