## 七、云原生 CI/CD 集成（联动 container-security-testing）

### 7.1 集群内 Runner/构建容器逃逸
```
# 自托管 Runner / Kaniko / buildkit 构建环境 = 集群内可控容器
# 逃逸路径: 特权容器、hostPath 挂载、docker.sock、CAP_SYS_ADMIN、内核CVE
#   （完整手法见 container-security-testing 技能）
# 拿 runner 节点 → 节点上 kubelet 凭据 → 集群控制
```

### 7.2 ServiceAccount 与镜像拉取凭据
```
# 构建环境注入的 SA token:
cat /var/run/secrets/kubernetes.io/serviceaccount/token
# kubeconfig 常挂载在 CI 配置中（构建脚本/secret）
# imagePullSecret 窃取 → 上游 registry 控制
# K8s RBAC: 构建 SA 常过度授权（list pods/create deployments）
```

### 7.3 从 CI 到集群到云的完整链（示范）
```
# 1) 攻 CI（Jenkins CVE-2024-23897/GitHub Actions 注入）→ 执行
# 2) 提取云 OIDC token / AK / kubeconfig
# 3) 换取云临时凭据（AssumeRoleWithWebIdentity / 云 metadata）
# 4) 云控制面 → S3/KMS/SecretManager 全量凭据 → 生产数据
# 5) 或直接 K8s 集群 → workload 横向 → 生产应用
# 这解释了为什么红队把 CI/CD 排在最高优先级目标
```

