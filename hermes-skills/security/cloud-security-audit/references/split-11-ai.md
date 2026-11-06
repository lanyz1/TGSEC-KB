## 十、云上 AI 服务攻击面

### 10.1 托管LLM平台（AWS Bedrock / Azure OpenAI / Vertex AI / 阿里云百炼）

**AWS Bedrock 已验证的 8 条 IAM 攻击向量（XM Cyber 2026.03）：**
```
1. 模型调用日志重定向：bedrock:PutModelInvocationLoggingConfiguration + s3:DeleteObject
   → 把全量提示词/响应日志改导向攻击者桶 + 销毁原有取证证据
2. Knowledge Base 凭据窃取：bedrock:GetKnowledgeBase 返回的集成凭据
   （连接Pinecone/Redis/Aurora/Redshift的凭据）→ 直接接管向量库
3. 知识库数据源投毒：篡改 SharePoint/Salesforce/Confluence/S3 数据源 → 污染RAG答案
4. Agent 直接注入：给Bedrock Agent输入含恶意指令的prompt → Agent调用外部API/读S3
5. Agent 间接注入：知识库中的恶意文档污染Agent决策（连供应链）
6. Flow 劫持：bedrock:UpdateFlow → 篡改自动化流程逻辑
7. Guardrail 禁用：bedrock:DeleteGuardrail / UpdateGuardrail → 移除内容过滤与合规控制
8. 模型访问滥用（LLMjacking）：用盗用凭据调用基础模型，单日成本最高$46,000
```

**LLMjacking 检测与利用：**
```bash
# 盗用凭据后枚举可用的模型与区域
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
aws bedrock invoke-model --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --body '{"prompt":"Hello","max_tokens":10}' --cli-binary-format raw-in-base64-out out.json
# 特征：模型调用日志默认关闭 → 取证盲区，攻击者常先做这步再行动
```

**其他托管LLM风险：**
- **模型提取**：通过API黑盒查询复制精调模型功能（影子模型）
- **训练数据提取**：诱导模型吐露训练语料中的敏感数据
- **Azure OpenAI / Vertex AI**：API key泄露、部署未设配额（成本炸弹）、内容过滤配置缺失
- **AI Agent（2025年攻击热点）**：Memory poisoning（长期记忆投毒，跨会话持久）、间接Prompt注入
  （ForcedLeak CVE：Salesforce Agentforce间接注入泄露CRM数据，CVSS 9.4）

### 10.2 向量数据库攻击

```
1. 未授权访问（最高频）：向量库默认无认证/弱认证
   - Milvus CVE-2025-64513（CVSS 9.3）：单HTTP头固定常量绕过全部认证，存在公开PoC扫描器
   - Chroma：2025年调查发现1,170+个公网可达实例，约1/3暴露生产数据无认证（Pwn2Own Berlin
     2025 AI类目靶标之一）
   - Qdrant 官方文档自认默认不安全；Weaviate v1.29.0才加入RBAC；Pinecone namespace不是安全边界
2. Embedding反转（Vec2Text）：92%的32-token文本可从embedding精确重建 → 向量泄露=原始数据泄露
3. 知识库投毒（PoisonedRAG，USENIX Security 2025）：注入5个恶意文档到百万文档库，
   攻击成功率90-99% → 污染RAG答案/窃取信息/诱导转账
4. 语义欺骗：构造语义相近的恶意向量劫持检索结果
5. 云上向量库（Pinecone/Qdrant Cloud/Azure AI Search）API key泄露 → 读库/删库/改写
```

```bash
# 向量库未授权探测
curl http://<host>:8000/api/v1/collections   # Chroma
curl http://<host>:19530/v2/vectordb/collections/list  # Milvus
# OWASP LLM Top10 (2025版) LLM08: Vector and Embedding Weaknesses 已官方收录
```

### 10.3 AI 基础设施与模型供应链

```
1. GPU容器工具链逃逸：NVIDIA Container Toolkit（CVE-2025-23266 NVIDIAScape CVSS 9.0，
   37%云环境受影响；三行Dockerfile：LD_PRELOAD注入）→ 逃逸后窃取模型权重
2. 模型文件投毒（存储层）：MinIO CVE-2025-31489 任意覆盖写 → 替换.pt/.safetensors →
   加载即RCE（字节跳动实习生投毒事件同源风险）
3. 模型注册表/仓库（HuggingFace私有部署/云托管）：弱认证、恶意模型上传、pickle反序列化
4. 暴露的AI工具服务：10,000+ 未认证Ollama、2,000+ Redis、200+ ChromaDB（Trend Micro 2025）
5. AI Agent沙箱逃逸：Bedrock AgentCore Code Interpreter沙箱逃逸（2025.09），
   "无网络"配置下仍可DNS外带数据；CVE-2026-4269 AgentCore恶意S3构建产物RCE
```

