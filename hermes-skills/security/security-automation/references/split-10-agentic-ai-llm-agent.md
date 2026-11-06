## 八、Agentic AI 安全自动化（LLM Agent 编排扫描/响应）

### 8.1 Agentic 与自动化/副驾的本质区别
| 类型 | 谁决定下一步 | 代表 |
|------|------------|------|
| SOAR 自动化 | 人类预先编写剧本 | Splunk SOAR、XSOAR |
| Copilot 副驾 | 人类运行时决策，AI 辅助 | Microsoft Security Copilot |
| **Agentic** | **系统基于实时证据自主推理决策，在受控边界内行动** | D3 Morpheus、Cortex AgentiX、Torq HyperAgents |

### 8.2 LLM Agent 编排扫描（Red/蓝通用）
```
用户指令(自然语言) → Agent规划(拆解任务) → 工具调用(nuclei/子域/指纹/查漏洞库)
  → 结果分析 → 下一步决策(扩大范围/验证/跳过) → 输出结构化报告
```
```python
# Agent 工具调用示意（LangChain/CrewAI 风格）
from langchain.tools import tool

@tool
def run_nuclei(target: str, severity: str = "high") -> str:
    """对目标执行 nuclei 扫描，返回 JSONL 结果"""
    # 实际实现：subprocess 调用 nuclei，解析输出
    ...

@tool
def lookup_cve(cve_id: str) -> str:
    """查询 CVE 详情与 PoC 信息"""
    ...

# Agent 循环：plan → act → observe → re-plan
```

### 8.3 LLM Agent 编排响应（蓝队）
```
告警进入 → Agent调查(查日志/查资产/查威胁情报) → 形成结论(严重度+置信度)
  → 分级响应：
     低危/确定误报 → 自动关闭(附理由)
     中危 → 转人工队列(附调查摘要)
     高危 → 隔离/封禁(需HITL审批) + 生成报告
```
**成熟实践（2026 实证）**：Databricks 用 17 个**源特定 Triage Agent**（每个 Agent 只负责单一检测源）+ 共享威胁情报 Agent，低危告警全量自动 Triage，升级率 ~3.2%，30 天节省 6500+ 分析师小时。**单一通用 Agent 处理全量告警会退化为另一种噪声（升级率 50%），源特定 Agent 才是有效形态。**

### 8.4 Agent 架构模式
- **多智能体协作**：规划 Agent / 执行 Agent / 验证 Agent / 情报 Agent 分工，结果交叉复核
- **ReAct 循环**：Reasoning → Acting → Observation，每一步都有观察反馈
- **技能化**：把安全操作封装为 Skill/工具（如本技能集），Agent 按需加载，节省 token
- **记忆与上下文**：案件级记忆（跨会话续查）+ 知识库检索（RAG 检索 runbook/历史案件）

### 8.5 自主等级与 HITL（安全运营）
| 等级 | 行为 | 适用 |
|------|------|------|
| AL1 建议 | Agent 仅给建议，人执行 | 初期/高风险动作 |
| AL2 审批 | Agent 执行到关键动作停下等人审批 | 半自动（HITL） |
| AL3 授权内自动 | 白名单动作内自动执行 | 低危、高频、确定动作 |
| AL4 自主 | 全流程自主 | 受限环境（靶场/隔离网段） |

**红线**：封禁生产、隔离核心资产、禁用特权账号、外发数据等动作默认 AL2，白名单之外的 AL3/AL4 必须经安全委员会审批。

### 8.6 Agentic 安全自动化风险与边界
- **幻觉**：Agent 可能编造不存在的"发现"→ 强制**exploit-validated**（执行 PoC 验证后才算数），低置信度必须标注
- **提示注入**：外部输入（日志/网页/邮件）可诱导 Agent 执行恶意动作 → 工具输入做白名单/净化，敏感上下文不直接进 prompt
- **权限失控**：Agent 只应持最小权限的**服务账号**（API Key 隔离、网络策略限制），绝不能复用人类管理员凭据
- **动作可逆性**：优先可逆动作（撤销 Token>禁用账号>删数据），不可逆动作必须人工
- **审计留痕**：Agent 每一步推理与工具调用全量落日志，可回放、可追责
- **成本与延迟**：LLM 调用昂贵，规则先行过滤 90%+ 事件，LLM 只处理剩余 5%-10%

