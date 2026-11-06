## 七、SOAR 深度实践（剧本编排/案件管理）

### 7.1 SOAR 架构与能力演进
```
编排层(Orchestration): API 连接 SIEM/EDR/身份/邮件/防火墙/威胁情报
自动化层(Automation):  剧本执行引擎（全自动/半自动/手动）
响应层(Response):      案件管理、告警队列、处置动作、审计留痕
```
**2025-2026 演进**：SOAR 不再是独立孤岛，已内嵌进 SIEM/XDR（如 Splunk SOAR 与 ES 8.0 统一负载、Microsoft Sentinel 集成、Palo Alto Cortex AgentiX）；新增**自然语言剧本创建**与**提示驱动自动化**（Prompt-driven automation：直接向外部团队/工单系统推送处置请求）。

### 7.2 剧本编排（Playbook）
**剧本要素**：触发器（SIEM 告警/定时/Webhook）→ 条件分支 → 动作（查询/封禁/通知）→ 人工审批节点 → 超时与失败处理。

```yaml
# 暴力破解调查剧本（示意，YAML 化描述）
name: brute-force-investigation
trigger: SIEM 告警 "Multiple Failed Logins"
steps:
  - action: 查询来源IP威胁情报(AbuseIPDB/MISP)
  - action: 查询账号最近登录记录
  - action: 查询资产关键性(CMDB)
  - if: IP信誉=恶意 AND 账号=特权
    then: [隔离主机(HITL审批), 封禁IP, 禁用账号, 通知安全负责人]
  - else: [打标"预期行为", 关闭案件]
  - action: 生成案件报告与证据快照
```

### 7.3 案件管理（Case Management）
- 告警→案件自动关联（同源/同资产/同攻击链聚合为一个案件）
- 案件生命周期：新开→调查中→处置中→已关闭(含误报关闭原因分类)
- 证据留痕：每个动作记录操作者（人或 Agent）、时间、参数、结果 → 审计完整
- 关键实践：**误报关闭必须填写原因分类**（规则过宽/预期行为/环境变化），数据反哺规则调优

### 7.4 SIEM/XDR 集成要点
- 统一事件模型：OCSF（Open Cybersecurity Schema Framework）正在成为跨源标准化事实标准，早期归一化可大幅降低剧本复杂度
- 富化先行：剧本第一步统一做上下文富化（资产、用户、IP 信誉、关联事件），后续所有分支共用
- 限流与风暴保护：同一资产高频告警在剧本入口聚合，防止剧本被告警风暴打爆

### 7.5 自适应剧本（LLM 增强）
静态剧本的局限：对未知攻击形态无法响应。2026 趋势是**运行时生成剧本**：LLM 基于实时证据动态决策下一步（查什么、问什么、封什么），但必须在**规则边界+动作白名单+审批闸门**内执行，详见第八章。

