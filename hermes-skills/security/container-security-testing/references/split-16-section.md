## 十五、测试检查清单

### 15.1 镜像与供应链
- [ ] 镜像漏洞扫描（CVE，TRIVY/GRYPE 交叉）
- [ ] 镜像敏感信息检测（密钥/凭据/Token/私钥，trivy secret）
- [ ] Dockerfile 审计（非 root/最小层数/无密钥/dockerignore）
- [ ] 镜像 digest 固定与 tag 漂移检查（防投毒）
- [ ] 供应链投毒 digest 比对（如 trivy 0.69.4-0.69.6 恶意镜像）
- [ ] 签名验证测试（cosign verify 是否被强制）
- [ ] SBOM 生成与依赖漏洞核对

### 15.2 Docker Daemon
- [ ] Docker Remote API 未授权（2375/2376）
- [ ] Docker Socket 挂载检测（容器内 .sock）
- [ ] BuildKit/构建环境权限检查

### 15.3 容器逃逸
- [ ] 特权容器测试（设备/cgroup/mount）
- [ ] CAP 审计（SYS_ADMIN/SYS_PTRACE/SYS_MODULE/DAC_READ_SEARCH）
- [ ] cgroup v1 notify_on_release 测试
- [ ] 危险挂载测试（/、/etc/hosts、/proc、docker.sock）
- [ ] PID/Network namespace 共享测试（--pid=host/--net=host）
- [ ] 内核漏洞面探测（uname + seccomp 状态 + 已知 CVE 匹配）
- [ ] runc/containerd 版本核对（CVE-2025-31133/52565/52881 修复版本）
- [ ] user namespace/rootless 配置核查

### 15.4 Kubernetes
- [ ] API Server 匿名/未授权访问测试
- [ ] etcd 2379 暴露测试
- [ ] Kubelet 10250/10255 未认证测试
- [ ] ServiceAccount Token 权限枚举（auth can-i --list）
- [ ] RBAC 高危权限审计（cluster-admin/通配符/secrets get/pods/exec/nodes/proxy/impersonate）
- [ ] nodes/proxy GET → kubelet /exec 提权测试（WebSocket）
- [ ] 特权 Pod 创建逃逸测试（PSA/Admission 是否拦截）
- [ ] NetworkPolicy 覆盖测试（默认全通？CNI 是否支持？）
- [ ] 服务网格 mTLS 强制模式测试（permissive 绕过）
- [ ] ingress-nginx 配置注入 CVE 测试
- [ ] Secret/ConfigMap 可读性验证
- [ ] 云元数据服务可达性（169.254.169.254）
- [ ] IRSA/Workload Identity 授权边界测试

### 15.5 运行时与进程
- [ ] 进程注入（nsenter/ptrace）能力测试
- [ ] 内存马注入测试（Java 容器）
- [ ] 容器内凭据/密钥收割测试
- [ ] eBPF 可用性检查（bpf syscall + CAP_BPF）
- [ ] eBPF rootkit/检测规避对抗演练（授权范围）

### 15.6 AI 基础设施
- [ ] Ollama/推理服务器未授权 API 测试（11434/8000/8080）
- [ ] 向量数据库未授权访问测试（ChromaDB/Redis）
- [ ] GPU 容器运行时漏洞面检查（NVIDIA Container Toolkit）
- [ ] MCP 服务器/Agent 平台暴露测试（Flowise/n8n）
- [ ] 模型仓库投毒/恶意模型拉取链路核查
- [ ] AI 服务出网/SSRF 面测试（推理服务器外拉端点）

