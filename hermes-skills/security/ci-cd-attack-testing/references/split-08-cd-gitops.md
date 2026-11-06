## 六、CD/发布平台攻击（GitOps）

### 6.1 ArgoCD 攻击
```
# 6.1.1 识别: 端口8080/8081、/applications、header x-argocd
# 6.1.2 CVE-2024-37152（/api/v1/settings 未认证访问, CVSS 5.3）
curl https://argocd/api/v1/settings
#   → 泄露 passwordPattern（密码策略）→ 辅助爆破/构造账号接管
#   → 配合会话操纵可实现持久化（Upwind 研究: 组合漏洞接管 EKS 集群）
# 6.1.3 CVE-2024-40634（/api/webhook 未认证 DoS, CVSS 7.5）
#   未认证超大 JSON payload + X-GitHub-Event: push → OOM 打瘫 argocd-server
# 6.1.4 CVE-2023-22482（OIDC audience claim 未校验, CVSS 9.8）
#   任意 OIDC provider 签发的 token 被接受 → 伪造组声明提权管理员
# 6.1.5 CVE-2023-22736（sharding 时命名空间授权绕过）
#   apps-in-any-namespace 场景下可部署到未授权 namespace
# 6.1.6 CVE-2023-25163（错误信息泄露仓库访问凭据）
# 6.1.7 CSRF→集群接管（Upwind 披露）
#   未启用同源检查的 CSRF → 诱导管理员/自调用 API → 部署恶意 Application →
#   在集群执行任意工作负载（含 kube-system 权限面）
# 6.1.8 通用面: 弱口令 admin/默认、repo 凭据泄露、project 权限模型绕过
# 6.1.9 利用链: 控制 ArgoCD = 控制所有被管集群的部署 → 供应链最高点
```

### 6.2 Flux/Helm 攻击
```
# Helm: 仓库投毒（helm repo add 恶意源）、chart 内嵌 k8s 后门清单
#   chart 的 post-install hook 可执行任意 pod
# Flux: Source/HelmRepository 指向被控源 → 拉取恶意 chart
#   Kustomization/HelmRelease 变更权限滥用
# 通用: GitOps 仓库写权限=部署控制权（改 manifest → 生产变更）
# 注意: 控制"GitOps 仓库"比控制平台更隐蔽且持久
```

### 6.3 Spinnaker/Octopus 等其他发布平台
```
# Spinnaker: 未认证 API(Gate/Sigma)、pipeline 任意执行、云账号凭据读取
# Octopus Deploy: 弱口令/API key、变量（含密码）读取
# 通用: 发布审批绕过（API直调/绕过人工审批 stage）、审计日志缺失
```

### 6.4 发布审批与审计绕过
```
# 目标: 跳过人工审批直接部署恶意版本
# 手法: API 直调（绕过 UI）、修改 pipeline 配置（移除审批stage）、
#       利用 SCM 触发免审批路径、利用低权限账号的"跳过审批"权限、
#       时间窗口攻击（审批人不在时提交）
# 持久化: 在审批通过路径上预埋恶意步骤（审核只看到"正常"diff）
```

