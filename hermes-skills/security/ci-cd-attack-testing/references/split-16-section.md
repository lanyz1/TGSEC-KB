## 十四、修复建议（高级）

- **平台加固**：CI/CD 平台不暴露公网（或仅经 SSO+IP 白名单）、强制 MFA（2FA 可阻断 GitLab 7028 类）、及时打补丁（KEV 清单优先）
- **最小权限**：GITHUB_TOKEN/CI_JOB_TOKEN 最小化（contents:read 而非 write）、secrets 仅注入需要的 job、Runner 隔离（专用 Runner + 命名空间隔离）
- **流水线硬化**：所有可控输入加引号/白名单、禁止不可信输入进表达式、action 固定 commit SHA、禁止 pull_request_target 处理不可信代码
- **依赖安全**：锁定版本+lock 文件、私有源优先（杜绝依赖混淆）、内部包名注册公共源占位、启用签名验证（cosign/sigstore/npm provenance）
- **制品安全**：镜像/制品不可变 tag + 摘要校验、Registry 强认证、镜像层扫描（含历史层 secrets）
- **CD/GitOps**：ArgoCD 等强制 SSO/audience 校验、仓库写权限分级、部署审批不可绕过、webhook 请求体大小限制
- **凭据治理**：云 AK 用短期凭据（OIDC/角色）、密钥轮换、构建环境不落盘长期凭据
- **开发者端**：开发者机器纳入 EDR、Git 凭据用硬件/系统级保护、IDE 扩展来源审计、MFA 全覆盖
- **供应链监控**：上游 action/依赖变更告警（Dependabot/OSV）、制品 provenance 验证、发布前供应链审计
- **检测告警**：监控异常构建（新任务/新 Runner/新依赖）、Secrets 泄露检测（GitHub secret scanning）、ArgoCD/CI 平台异常 API 调用

