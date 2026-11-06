## 十五、修复建议与加固

### 15.1 身份与访问（最高优先级）
- **最小权限**：IAM/RAM策略仅授必要权限；拒绝"*"动作+通配资源；定期用prowler/LLM策略审计
- **信任策略收紧**：Principal限定具体ARN；OIDC的sub/aud精确匹配仓库与分支；禁用StringEqualsIfExists滥用
- **PassRole治理**：使用 `iam:PassRole` 的 `iam:PassedToService` 与资源级条件约束；审计谁持有PassRole
- **强制MFA**：所有管理员/敏感操作强制MFA；警惕MFA旁路（会话cookie窃取、vishing）
- **短时凭据**：全面使用STS/角色替代长期AK；定期轮转并清理未用AK
- **管理账号加固**：Organizations管理账号独立、强管控；限制sts:AssumeRoot使用场景
- **OIDC护栏**：参考AWS 2025年6月默认护栏，存量易受攻击角色必须人工审计修复

### 15.2 数据与存储
- **存储桶私有化**：禁止匿名读写；开启版本控制+访问日志；CORS最小化
- **加密**：服务端加密（SSE-KMS）+传输加密；KMS密钥策略收紧
- **快照/备份**：禁止公开共享；删除保护开启；备份走不可变存储
- **数据库**：关闭PubliclyAccessible；白名单最小化；强制SSL；禁用默认弱口令

### 15.3 网络与计算
- **IMDSv2强制**：仅允许IMDSv2+Token；容器/无服务器环境隔离元数据访问
- **安全组/NACL**：最小开放；SSH/RDP仅限堡垒机；VPC端点私有化访问云服务
- **K8s**：启用Pod Security Admission/seccomp/AppArmor；限制hostPath/privileged；网络策略默认拒绝；镜像签名准入
- **容器运行时**：及时更新runc/containerd（2025年三漏洞）与NVIDIA Container Toolkit（NVIDIAScape）

### 15.4 云上AI
- **Bedrock等托管LLM**：启用模型调用日志；Guardrail强制；Knowledge Base连接凭据用密钥托管；限制bedrock:*写权限
- **向量库**：开启认证与RBAC；不暴露公网；API key最小权限与轮换
- **模型供应链**：镜像/模型文件哈希校验+签名；存储桶写权限最小化（防MinIO类投毒）
- **AI Agent**：权限最小化；输出/工具调用审计；防内存投毒与间接注入

### 15.5 供应链与CI/CD
- GitHub Actions：第三方Action固定commit SHA；禁pull_request_target处理fork代码；permissions最小化；OIDC临时凭据
- 依赖安全：锁文件+私服+依赖混淆防护；npm/pypi包签名验证
- 镜像：cosign签名+SBOM+准入控制器校验

### 15.6 日志与检测
- 全区域CloudTrail/ActionTrail/Activity Log启用，管理事件+数据事件全覆盖
- 日志桶不可变（Object Lock/WORM）+多副本外置；对 StopLogging/DeleteTrail 即时告警
- GuardDuty/态势感知+行为基线；覆盖ATT&CK v18云矩阵（K8s/CI/CD/云数据库）
- 备份与恢复演练；针对"删库+删备份"勒索流程设计隔离恢复环境（CIRE）

