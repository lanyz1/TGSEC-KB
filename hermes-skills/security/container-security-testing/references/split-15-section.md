## 十四、工具链

```bash
# 镜像/供应链安全
trivy              # 镜像漏洞+secret+SBOM 扫描（注意官方镜像曾被投毒，固定 digest）
grype / syft       # 漏洞数据库 / SBOM 生成
dive               # 镜像层交互分析
dockle / hadolint  # 镜像 CI 审计 / Dockerfile lint
cosign             # 镜像签名与验证
checkov            # IaC 安全扫描（Dockerfile/K8s/Helm/Terraform）
oras               # OCI 仓库操作（供应链取证）

# 容器运行时探测与逃逸
CDK                # 容器渗透工具集（evaluate/k8s 利用一键化）
deepce             # 容器逃逸自动检测利用
amicontained       # 容器权限/capabilities 探测
kdigger            # 容器内 K8s 环境探测
nsenter / capsh / unshare   # 基础逃逸原语

# 运行时检测（红队对抗视角，了解检测面）
falco              # syscall 级威胁检测
tracee             # eBPF 安全追踪
tetragon           # 内核态强制执行
sysdig             # 系统调用监控

# K8s 攻防
kube-hunter        # K8s 渗透测试（未授权/安全配置）
kubescape          # K8s 合规/风险扫描（NSA/MITRE 框架）
kubeaudit          # 部署清单审计
peirates           # K8s 渗透/提权工具集（SA Token、nodes/proxy 利用）
boopkit            # eBPF 内核级后门（K8s 逃逸+隐蔽持久化）
rbackup            # RBAC 攻击路径枚举
kube-forensics     # 集群取证/渗透辅助
kdigger            # Pod 内探测工具
kubeletctl         # Kubelet API 利用（10250/exec）
Kerberos 等非本域    # 略

# AI 基础设施安全
AIMap (Bishop Fox) # AI 暴露服务测绘（Ollama/MCP/Gradio/Flowise 指纹）
Ollama API 探测     # /api/tags /api/generate 未授权验证
ffuf / nuclei      # 通用指纹与漏洞验证（AI 服务专用模板）
```

