## 九、多云、混合云与云供应链攻击

### 9.1 多云与身份联邦攻击

```
1. 身份联邦信任链（SAML/OIDC/SCIM）：
   - 企业IdP（Okta/Entra/钉钉/企业微信）→ 云SSO：IdP被攻破=所有云被接管
   - 云SSO信任策略过宽：允许任意组/角色映射
2. 跨云信任：AWS Organizations ↔ GCP/Azure 的联合身份配置错误
3. 多账号/多租户蔓延：Org/管理组/subscription 管理入口未加固（单点接管）
4. 云间复制/迁移管道：数据迁移任务中凭据与访问控制被忽略
5. SaaS层信任：Salesforce/Slack/Workday集成OAuth token（UNC6395：700+租户数据被窃）
```

### 9.2 混合云攻击面

```
1. VPN/专线（Express Connect/专线/VPN网关）：配置错误/弱认证/未打补丁的VPN设备 → 云内网入口
2. IDC↔云：云上VPC对IDC网段的信任（安全组放行全部IDC IP）→ IDC失陷=云内网失陷
3. 混合云DNS：云内DNS解析到IDC内网地址 → DNS重绑定绕过
4. AD域同步：云上AD连接器/密码哈希同步（AD Connect）→ 云上身份=域身份
5. 云备份↔本地：备份链路弱加密/弱认证
```

### 9.3 云供应链攻击（第三方云服务/镜像/依赖）

**攻击链与案例：**
```
1. 依赖投毒 → CI/CD执行 → 云凭据窃取 → 云接管：
   - s1ngularity（nx npm投毒，2025.08）：postinstall窃取环境变量/AI工具凭据（QUIETVAULT）
     → UNC6426 借GitHub→AWS OIDC信任72小时拿下AWS管理员
   - tj-actions/changed-files（CVE-2025-30066）、reviewdog/action-setup（CVE-2025-30154）：
     第三方GitHub Actions投毒影响23,000+仓库
   - TanStack事件（CVE-2026-45321）：pull_request_target链式利用，首个带有效SLSA L3
     证明的恶意npm包（自传播蠕虫，170+包受影响）
2. 镜像投毒：恶意基础镜像/Docker Hub抢注/镜像拉取劫持 → 生产集群执行
3. 依赖混淆：私服缺失时，同名公共包（dependency confusion）→ 供应链RCE
4. 第三方云服务供应商：使用SaaS/外包云管理服务 → 供应商失陷=客户云失陷（连坐）
```

**供应链审计命令：**
```bash
# GitHub Actions 供应链审计
# 1. 检查工作流中第三方Actions是否固定commit SHA
grep -r "uses:" .github/workflows/ | grep -v "@"  # 未固定版本=风险
# 2. 检查 pull_request_target 使用（危险footgun）
grep -r "pull_request_target" .github/workflows/
# 3. 检查 OIDC 信任策略（AWS侧）
aws iam list-roles --query 'Roles[].AssumeRolePolicyDocument' --output json | grep -i oidc
# 4. 检查工作流权限最小化
grep -r "permissions:" .github/workflows/

# 镜像供应链扫描
trivy image --severity HIGH,CRITICAL <image>
cosign verify --key <pubkey> <image>   # 签名验证
docker sbom <image>                     # SBOM清单
```

