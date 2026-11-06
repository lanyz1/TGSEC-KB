## 十六、修复建议

- **最小权限**：容器非 root 运行（USER 指令）、最小 CAP 集合、`automountServiceAccountToken: false`
- **只读根文件系统**：`readOnlyRootFilesystem: true` + `securityContext.allowPrivilegeEscalation: false`
- **Pod 安全标准**：启用 Pod Security Admission（baseline/restricted 级），或 Kyverno 强制（禁 privileged/hostPath/hostPID/hostNetwork）
- **seccomp/AppArmor**：K8s 1.27+ 默认 `seccompRuntimeDefault`；拦截 bpf syscall；`kernel.unprivileged_bpf_disabled=2`
- **网络隔离**：默认拒绝 + 显式放行；确认 CNI 支持 NetworkPolicy（Calico/Cilium）；服务网格切 STRICT mTLS
- **RBAC 最小化**：业务 SA 绝不绑 cluster-admin；审计 6 大提权链权限；`nodes/proxy` 用 K8s v1.36+ 细粒度 kubelet 授权（KEP-2862）替代；`system:masters` 组严格管控；`automountServiceAccountToken` 按需关闭
- **镜像供应链**：镜像按 digest 拉取（防 tag 漂移）；Cosign/Notary 签名 + Kyverno 准入强制校验；CI 流水线 secrets 用 Vault/Secret Manager 动态注入，禁止嵌入镜像层；SBOM 全链路留存；对 CI/CD 使用的高危镜像（含扫描器自身）做行为监控
- **运行时防护**：Falco/Tetragon/Tracee 实时监控（特权提升、逃逸特征 syscall、新 eBPF 加载）；eBPF 加载审计（auditd bpf 规则）；对特权 Pod 设专用污点/容忍（Taints+Toleration）缩小爆炸半径
- **网络策略**：默认拒绝 + 显式放行（Calico/Cilium）；高危服务加 L7 策略（CiliumNetworkPolicy）；服务网格 STRICT mTLS + AuthorizationPolicy
- **Secret 管理**：etcd 静态加密；Secret 用 HashiCorp Vault / External Secrets Operator / cloud KMS；轮换 SA Token 与云凭据
- **控制平面加固**：API Server 禁匿名访问；etcd 仅限内网 + TLS 客户端认证；kubelet 10250 仅限必要主体访问；ingress-nginx 升级 + 注解白名单；开启审计日志并送 SIEM
- **云侧**：元数据服务防护（IMDSv2）；IRSA/Workload Identity 最小授权；节点角色 IAM 最小化
- **AI 基础设施**：Ollama/推理服务器不监听 0.0.0.0（或强制认证 + 反代）；向量库/模型仓库强制认证与来源校验；推理服务器按互联网边缘资产管理（紧急补丁 SLA）；模型加载禁止 pickle（用 safetensors）

