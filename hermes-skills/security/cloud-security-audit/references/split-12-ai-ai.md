## 十一、AI 大模型结合：AI 辅助云攻防

### 11.1 AI 辅助云配置审计（防御/审计视角）

**用 LLM 分析 IAM 策略与云资源导出找问题：**
```bash
# 1. 导出云资源清单
# AWS：使用 prowler / cloudsploit 导出，或用 config 快照
prowler aws -M json > audit.json
# 2. 导出IAM策略
aws iam list-policies --scope Local --output json > policies.json
aws iam get-account-authorization-details --output json > authz.json
# 3. 交给LLM分析（提示词框架）：
#    - "从policies.json中找出所有允许'*'动作或'*'资源的策略，标注被谁引用"
#    - "分析authz.json中的信任策略，找出Principal为'*'或OIDC sub未限定的角色"
#    - "找出包含iam:PassRole/CreatePolicyVersion/AttachUserPolicy等提权动作的权限边界"
#    - "对照审计清单逐项输出风险等级与修复建议"
```
**LLM 审计价值点：**
- IAM 策略批量语义分析（人读千条JSON不可行，LLM可规模化找提权路径组合）
- 信任策略/条件表达式语义误判识别（StringEqualsIfExists 类）
- 云资源导出（配置快照）→ 识别公网暴露、加密缺失、版本控制关闭等基线问题
- 输出结构化风险报告 + 修复代码（Terraform/IAM Policy修正）

### 11.2 AI 驱动云攻击路径规划（攻击视角）

**AI 压缩"发现→决策→执行"链路（8分钟攻击案例证明有效性）：**
```
1. 凭据/枚举结果输入LLM → 自动生成权限提升路径排序（先试哪条提权链）
2. 根据 IAM 权限矩阵生成利用代码（如基于Lambda角色的提权函数）
3. 攻击操作自动化：批量AssumeRole尝试、策略注入payload生成
4. 数据外传方案优化：选择最隐蔽的通道（S3复制/云存储中继）
5. 对抗调整：根据报错信息自动改写命令（LLM驱动的交互式入侵）
```

**AI 辅助攻击特征（检测侧识别线索）：**
```
- 代码含LLM典型异常处理模式（except: pass包裹全部）
- 幻觉的GitHub URL/AWS账号ID（不存在但格式正确）
- session name 含 "claude-session"/"gpt" 等字样
- 命令执行速度远超人工节奏（分钟级批量操作）
```

### 11.3 大模型云服务攻击面（LLM 自身作为入口）

```
1. 面向LLM的云API（Bedrock/OpenAI/Vertex）key泄露 → LLMjacking/数据读取
2. LLM应用后端：RAG管道（向量库/存储）→ 前文第十章全链
3. AI编码工具链（Claude Code/Gemini CLI/Amazon Q）本地凭据文件 → 供应链窃取目标
4. AI Agent 权限过大：给Agent的云工具权限=给攻击者的权限（Agent间接注入接管）
5. 提示注入桥接云API：诱导Agent执行 sts:assume-role / S3读取等真实云操作
```

