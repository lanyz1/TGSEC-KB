## 九、AI 大模型安全运营（LLM 分析告警/降噪/剧本生成）

### 9.1 LLM 告警分析与降噪（三层管道）
```
Layer1 规则过滤:  确定性规则滤掉 90-95% 明确良性事件(健康检查/CI账号/计划任务)
Layer2 LLM Triage: 富化后的告警 → LLM 结构化判定(benign/suspicious/malicious + 置信度 + 理由)
Layer3 分级响应:   高危自动遏制 / 中危转人工 / 低危记录趋势
```
```python
# LLM Triage 结构化输出（示意）
from pydantic import BaseModel
from enum import Enum

class Disposition(str, Enum):
    ESCALATE = "escalate"; MONITOR = "monitor"; CLOSE = "close"

class TriageResult(BaseModel):
    severity: str          # critical/high/medium/low/info
    disposition: Disposition
    confidence: float      # 0-1，低于阈值不自动动作
    reasoning: str         # 一段结论性理由
    recommended_actions: list[str]
    false_positive_indicators: list[str]  # 支撑"关闭"判定的证据
```
**富化是命脉**：用户角色、资产关键性、IP 信誉、24h 关联告警、是否业务时间——"垃圾进垃圾出"，LLM 需要上下文才能避免把 Tor 出口节点当普通外部 IP。

### 9.2 降噪的工程要点
- **置信度阈值化**：LLM 输出数值置信度，低于阈值只打标不动作；高阈值才自动关闭/升级
- **已知良性模式语料**：维护 CI/CD 服务账号、定时任务、扫描器自身流量等"已知良性"清单，提示词中显式声明"这些模式不应告警"
- **每日误报率看板**：`误报率=确认误报/总告警`，规则或 Agent 调优后回测
- **关闭原因分类**：误报关闭必须归因，反哺规则与提示词优化

### 9.3 AI 辅助剧本生成与优化
- **自然语言生成剧本**：`"帮我写一个：检测到异常登录后，查询威胁情报，若是恶意 IP 则禁用账号并通知"` → LLM 生成结构化剧本 → 人工评审 → 沙箱回放（用历史告警回测）→ 灰度上线
- **剧本优化**：用历史案件数据训练/提示优化分支条件；回放引擎评估剧本在历史数据上的"该拦截的没拦/该放行的误拦"
- **检测规则生成**：从确认的攻击事件（红队 TTP/事后复盘）自动生成 Sigma/YARA/查询规则草案

### 9.4 双模型架构与安全 LLM 选型
```
战略大脑(通用大模型): 威胁研判、攻击链推理、复杂决策
战术专家(安全微调模型): 日志语义解析、ATT&CK 技术识别、实时告警分类(毫秒级)
```
- 开源安全模型：Cisco Foundation-sec 系列（8B 级模型经 prompt tuning 可达超大模型性能）、微软安全专用模型（基于安全遥测训练）
- 本地化部署考虑：数据不出域（合规）、延迟、成本
- **RAG 知识库**：runbook、历史案件、威胁情报(MISP)、内部检测笔记 → 检索增强，降低幻觉

### 9.5 提示词与输出规范
- 始终要求**结构化输出**（JSON Schema/Pydantic），下游不用解析自由文本
- 系统提示词声明角色（"你是资深 SOC 分析师，进行一线 Triage"）与判定规则
- 上下文裁剪：只投喂富化摘要（几 KB），不投喂 10KB 原始日志
- 关键结论要求 Agent **引用证据来源**（哪条日志/哪个查询结果）

