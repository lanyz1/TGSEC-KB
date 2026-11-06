## 十四、测试检查清单

### 14.1 侦察与资产枚举
- [ ] 完成子域名/证书/DNS被动枚举，识别云厂商
- [ ] 使用Shodan/FOFA检索公网暴露云资源（存储桶/数据库/K8s API/SSH/RDP）
- [ ] GitHub/gitleaks 扫描AK/SK/Token泄露（含AI工具凭据文件）
- [ ] 检查CI/CD日志、容器镜像层、前端JS中的凭据泄露
- [ ] 测试云存储桶（S3/OSS/Blob/GCS）匿名读写与枚举

### 14.2 IAM 与身份
- [ ] 枚举当前身份权限（sts get-caller-identity / 盲测枚举）
- [ ] 审计 IAM/RAM 策略是否存在过度授权（*动作/*资源）
- [ ] 测试提权路径：CreatePolicyVersion / PutUserPolicy / AttachUserPolicy / AddUserToGroup
- [ ] 测试 iam:PassRole 与 lambda:CreateFunction / ec2:RunInstances 组合
- [ ] 审计角色信任策略：Principal通配、OIDC sub/aud未限定、StringEqualsIfExists误用
- [ ] 检查 Organizations 管理账号防护与 sts:AssumeRoot 风险
- [ ] Azure：Service Principal权限、条件访问策略、目录角色分配
- [ ] GCP：服务账号actAs/密钥创建权限、Workload Identity
- [ ] 阿里云：RAM子账号过度授权、AttachPolicyToUser、PassRole

### 14.3 存储与数据
- [ ] 审计存储桶策略/ACL/版本控制/CORS（匿名读写、ListBucket公开）
- [ ] 测试预签名URL/STS临时凭据权限是否过大
- [ ] 测试Dangling DNS/Bucket接管
- [ ] 检查备份/快照是否公开共享（RDS/EBS/Cloud SQL快照）
- [ ] 检查数据库公网暴露与弱口令（RDS/Redis/Mongo/ES）

### 14.4 元数据与SSRF
- [ ] 测试SSRF访问各平台元数据端点（含Header要求）
- [ ] 检查IMDSv2是否启用、Token防护是否可绕过（IPv6/容器网络）
- [ ] 从元数据获取临时凭据并验证权限范围

### 14.5 容器与K8s
- [ ] 审计K8s RBAC（cluster-admin、过度SA权限）
- [ ] 测试API Server未授权/弱认证
- [ ] 检查Pod特权/hostPath/hostPID/Docker Socket挂载
- [ ] 检查镜像漏洞与供应链（trivy扫描、签名验证）
- [ ] 测试云托管K8s节点角色/Workload Identity权限

### 14.6 Serverless/托管服务/AI
- [ ] 审计Lambda/FC函数角色与触发器的过度授权
- [ ] 检查函数环境变量中的敏感配置
- [ ] 测试事件源注入（S3/SQS/API Gateway触发）
- [ ] 审计托管LLM（Bedrock等）模型调用权限与日志配置
- [ ] 测试向量数据库未授权访问与知识库投毒
- [ ] 检查AI Agent权限边界与提示注入面

### 14.7 供应链与CI/CD
- [ ] 审计GitHub Actions工作流：第三方Action固定版本、pull_request_target、权限最小化
- [ ] 审计OIDC联邦信任策略（sub/aud限定）
- [ ] 检查容器镜像来源与签名（cosign/SBOM）
- [ ] 检查依赖混淆风险（私服配置）

### 14.8 取证与对抗
- [ ] 确认审计日志启用范围与保留期（CloudTrail/ActionTrail/Activity Log）
- [ ] 测试日志完整性保护（S3 Object Lock/不可变存储）
- [ ] 记录检测规则覆盖面（GuardDuty/告警规则）与响应时间
- [ ] 验证 StopLogging/DeleteTrail 等动作是否触发告警

