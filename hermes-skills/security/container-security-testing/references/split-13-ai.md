## 十二、云原生 AI 攻击面

### 12.1 AI 基础设施攻击面全景（2025-2026 爆发）

```
态势：2025-03 国家网络安全通报中心通报 Ollama 默认配置安全隐患；
2026 初全球约 17.5 万 Ollama 实例公网暴露，91% 无认证（Bishop Fox AIMap / Intruder 扫描）。
AI 基础设施 = 容器 + GPU + 模型 + 数据，攻击面爆炸：
1. 推理服务器（Ollama/vLLM/LMDeploy/Triton/SGLang/llama.cpp）
2. 向量数据库（ChromaDB/Redis/Weaviate/Milvus/Qdrant）
3. 编排与 Agent 平台（Flowise/n8n/LangServe/OpenWebUI/Gradio）
4. MCP 服务器（Model Context Protocol，新供应链入口）
5. GPU 容器运行时（NVIDIA Container Toolkit/驱动）
6. 模型仓库（Hugging Face/ModelScope 恶意模型）
OWASP LLM Top 10 2025：LLM04 数据与模型投毒、LLM08 向量与嵌入弱点
```

### 12.2 GPU 容器攻击面

```
- NVIDIA Container Toolkit 漏洞（Pwn2Own 2025 展示）：容器挂载 GPU 时的逃逸链
  （libnvidia-container / nvidia-container-cli 特权辅助进程面）
- 测试：容器内 ls /dev/nvidia*；检查是否可读写 nvidia 驱动设备
- GPU 算力盗用：未授权调用 /v1/completions 免费推理（算力走私/挖矿）
- CUDA 相关：恶意 CUDA kernel 读取 GPU 显存中其他租户残留数据（多租户 GPU 共享）
```

### 12.3 Ollama 容器攻击面

```bash
# 未授权 API 探测
curl -s http://target:11434/api/tags                          # 模型列表
curl -s http://target:11434/api/show -d '{"name":"llama3"}'   # 模型元数据/泄露 license 信息

# 利用面：
# 1. /api/generate /api/chat：免费推理（算力盗用）→ 隐私数据投喂外泄
# 2. /api/pull：拉取恶意模型（模型即代码：GGUF 权重中植入后门/提示注入）
# 3. /api/create /api/push：篡改模型清单、泄露（推送模型到攻击者仓库）
# 4. 历史 RCE：CVE-2024-37032（路径遍历）、CVE-2024-39720/39722/39719/39721
# 5. 2026 新 CVE：CVE-2026-7482（GGUF 加载器堆越界读，泄露环境变量/API key/对话数据，CVSS 9.1）
# 6. Windows 更新链：CVE-2026-42248 + CVE-2026-42249（更新校验缺失+路径穿越 → 自动执行任意程序，CVSS 9.8）

# 防护（防御视角）：OLLAMA_HOST=127.0.0.1；反向代理 + API Key；网络层 IP 白名单
```

### 12.4 向量数据库与推理服务器

```bash
# ChromaDB/Redis 向量库：未授权 → 读取/篡改全部向量数据（RAG 投毒根源）
curl -s http://target:8000/api/v1/collections
redis-cli -h target -p 6379 info                              # 未授权 Redis（含向量模块）

# 推理服务器反序列化/SSRF 面（2025-2026 密集披露）：
# - LMDeploy CVE-2026-33626：SSRF（外部拉取端点无 URL 校验），披露 12 小时内被武器化
# - vLLM CVE-2025-30165 / TensorRT-LLM CVE-2025-23254：IPC 通道不安全反序列化
# - ShadowMQ（2025-11，Oligo）：ZeroMQ+pickle 反序列化模式被十几个推理框架复制粘贴 → 系统性 RCE 类
# - Flowise CVE-2025-59528（CVSS 10.0）：CustomMCP 任意 JS 注入 → Node.js 全权限 RCE，1.2 万+ 实例
# - Pwn2Own Berlin 2025：Redis 向量库（过时 Lua 组件）、NVIDIA Container Toolkit
```

### 12.5 MCP 与 Agent 供应链

```
- CVE-2025-6514（CVSS 9.6）：mcp-remote OAuth 漏洞 → RCE，43.7 万环境受影响
  （Claude Desktop/VS Code/Cursor 连接外部服务的桥梁被攻破 = AI 供应链投毒）
- 恶意 MCP 服务器：诱骗 Agent 连接 → 窃取对话/凭据/执行任意工具
- Agent 平台（n8n/Flowise）凭据集中 → 一处沦陷 = 全部集成服务凭据泄露
- 测试思路：扫描暴露的 MCP 端点（SSE/JSON-RPC），测试未认证调用、工具滥用、提示注入
```

