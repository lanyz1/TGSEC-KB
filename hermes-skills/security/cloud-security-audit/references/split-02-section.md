## 一、云资产枚举与攻击面映射

### 1.1 侦察阶段

**被动枚举：**
| 技术 | 工具 | 目标 |
|------|------|------|
| 子域名枚举 | Amass/Subfinder/CloudBrute | 发现云服务端点 |
| 证书透明度 | crt.sh/Censys | 发现云域名 |
| DNS枚举 | DNSRecon/DNSDumpster | CNAME到云服务（识别云厂商） |
| 搜索引擎 | Google Hacking/Shodan/FOFA/Quake | 暴露的云资源 |
| GitHub泄露 | git-hound/truffleHog/gitleaks | AK/SK/Token/密钥 |
| 云指纹识别 | CloudEnum/cloudbrute | 识别云服务商与资源名模式 |

**凭据泄露面（2025-2026新增重点）：**
```
1. GitHub/GitLab 代码库：硬编码AKSK（正则匹配）
   阿里云:  ^LTAI[A-Za-z0-9]{20}$
   腾讯云:  ^AKID[A-Za-z0-9]{32}$
   AWS:    (A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}
2. CI/CD 日志与配置：GitHub Actions secrets、Jenkins凭证、.env提交
3. 容器镜像层：docker history 泄露环境变量中的凭据
4. SaaS/第三方令牌：Slack/OAuth token、Salesforce集成凭据（UNC6395事件路径）
5. AI工具配置：Claude/Gemini CLI/Amazon Q本地凭据文件（QUIETVAULT专门窃取，含--dangerously-skip-permissions滥用）
6. 前端JS/小程序包：Webpack解包、逆向提取STS临时凭据
7. 错误页面/heapdump/备份文件泄露
```

**主动枚举：**
```bash
# AWS S3 Bucket枚举
aws s3 ls s3://bucket-name --no-sign-request
aws s3api list-buckets --profile target

# Azure Storage枚举
az storage blob list --container-name container --account-name account

# GCP Bucket枚举
gsutil ls gs://bucket-name

# 阿里云 OSS 枚举（ossutil2）
ossutil64 ls oss://bucket-name
```

### 1.2 云平台攻击面矩阵

| 攻击面 | AWS | Azure | GCP | 阿里云 |
|--------|-----|-------|-----|--------|
| 身份服务 | IAM | Entra ID(原Azure AD) | Cloud IAM | RAM |
| 对象存储 | S3 | Blob Storage | Cloud Storage | OSS |
| 计算 | EC2/Lambda | VM/Functions | GCE/Functions | ECS/FC |
| 数据库 | RDS/DynamoDB | SQL DB/Cosmos | Cloud SQL/BigQuery | RDS/OTS |
| 容器 | EKS/ECS | AKS | GKE | ACK |
| 消息队列 | SQS/SNS | Service Bus | Pub/Sub | MNS |
| Serverless | Lambda | Functions | Cloud Functions | FC |
| AI平台 | Bedrock/SageMaker | Azure OpenAI | Vertex AI | 百炼/DAS |
| 密钥管理 | KMS | Key Vault | Cloud KMS | KMS |
| 审计日志 | CloudTrail | Activity Log | Audit Log | ActionTrail |

### 1.3 权限枚举（拿到凭据后第一件事）
```bash
# AWS：我到底有什么权限
aws sts get-caller-identity
# 显式枚举（可能被拒）
aws iam list-attached-user-policies --user-name <user>
# 盲测枚举（enumerate-iam / pacu iam__bruteforce_permissions）
# 通过调用数百个只读API，以成功/失败推断权限矩阵
python3 enumerate-iam --access-key AKIA... --secret-key ...

# Azure
az account show
az ad signed-in-user show

# GCP
gcloud auth list
gcloud projects get-iam-policy <project-id>

# 阿里云
aliyun sts GetCallerIdentity
```

