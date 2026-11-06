## 概述

容器化是现代应用的基础架构，其安全模型建立在**共享内核**之上——容器与宿主机之间只有 namespaces/cgroups 的软隔离，没有虚拟化边界。因此，任何内核漏洞、运行时缺陷或过度权限配置，本质上都是容器逃逸的潜在路径。本技能以资深攻防专家视角，系统化覆盖**镜像供应链→构建/CI-CD→运行时→网络→编排层（K8s）→宿主机→云凭据**的全栈攻击链，从"单容器逃逸"升级到"集群接管 + 云账号接管"的完整 kill chain。

### 核心概念

- **容器 ≠ VM**：共享宿主机内核，`/proc`、`/sys`、设备、capabilities、syscall 都是攻击面；逃逸的本质是跨越 namespace/cgroup 边界触达宿主机内核态或文件系统
- **逃逸三要素**：命名空间隔离（PID/MNT/NET/UTS/IPC/USER/CGROUP）、Linux capabilities（CAP_SYS_ADMIN/CAP_SYS_PTRACE/CAP_NET_ADMIN 等危险 CAP）、内核攻击面（syscall/驱动/eBPF）
- **K8s 信任边界**：Pod 内 ServiceAccount Token → API Server 认证/授权 → RBAC 权限是集群内提权的核心杠杆；Node（kubelet）是集群与宿主机之间的桥头堡
- **默认信任是最大的漏洞**：K8s 默认扁平网络（任意 Pod 互通）、默认挂载 SA Token、默认允许 root 运行，这些"默认"就是攻击路径
- **攻击链分层**：镜像投毒（供应链）→ 应用漏洞（入口）→ 容器逃逸（隔离突破）→ 节点沦陷（kubelet 凭据）→ 集群接管（RBAC/SA Token）→ 云凭据（元数据服务/IRSA/Workload Identity）

### 2025-2026 威胁态势（时效情报）

- **runc 逃逸三连**：CVE-2025-31133 / CVE-2025-52565 / CVE-2025-52881（2025-11 披露，2026-06 确认在野利用），影响 runc 1.0.0-rc3 起全部版本，`core_pattern` 内核 upcall 提权 → 宿主 root
- **nodes/proxy GET → 集群 RCE**：2026-01 披露（Won't Fix），监控组件普遍持有的 `nodes/proxy GET` 权限经 WebSocket 绕过 CREATE 检查直达 kubelet `/exec`，69 个 Helm Chart 受影响
- **镜像供应链投毒进入"安全工具自身被投毒"时代**：aquasec/trivy 官方镜像 0.69.4~0.69.6 被投毒（2026-03），窃取 CI/CD secrets 与云凭据
- **AI 基础设施裸奔**：全球约 17.5 万 Ollama 实例公网暴露（2026-early），91% 无认证；推理服务器（vLLM/LMDeploy/Triton/SGLang）成为新攻击面，LMDeploy CVE-2026-33626 披露 12 小时内被武器化
- **K8s 攻击面向配置组件集中**：ingress-nginx 配置注入系列 CVE 持续（CVE-2025-1974 / CVE-2026-3288 / CVE-2026-24512 等），Admission Controller 成为 RCE 跳板

