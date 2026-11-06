---
name: container-security-testing
description: 容器安全深度攻防测试专业技能（v3.0高级版）：Docker/K8s全攻击面覆盖、2025-2026最新容器逃逸CVE深度利用（runc/containerd/kernel面）、K8s完整攻击链（API Server未授权→RBAC提权→kubelet exec→集群接管→云凭据）、镜像供应链深度攻击（注册表投毒/镜像层后门/签名绕过，联动ci-cd-attack-testing）、eBPF攻击面与检测规避、服务网格/网络策略绕过、云原生AI攻击面（GPU容器/Ollama/向量库/推理服务器）、AI大模型结合攻防（LLM辅助K8s配置审计与攻击路径规划）、从镜像审计到宿主机与云账号接管的完整攻击链
version: 3.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='container-security-testing', file_path='references/full.md')`

# 容器安全深度攻防测试技能

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、镜像安全深度审计与供应链攻击](references/split-02-section.md)
- [二、Docker Daemon 与 API 攻击面](references/split-03-docker-daemon-api.md)
- [三、容器逃逸技术全景](references/split-04-section.md)
- [四、2025-2026 最新容器逃逸 CVE 深度利用](references/split-05-2025-2026-cve.md)
- [五、Kubernetes 深度攻击链（API Server → 集群接管）](references/split-06-kubernetes-api-server.md)
- [六、RBAC 滥用与提权攻击路径](references/split-07-rbac.md)
- [七、Kubelet 攻击面与 nodes/proxy 深度利用](references/split-08-kubelet-nodes-proxy.md)
- [八、K8s 横向移动、持久化与后渗透](references/split-09-k8s.md)
- [九、命名空间隔离与网络策略/服务网格绕过](references/split-10-section.md)
- [十、eBPF 攻击面与检测规避](references/split-11-ebpf.md)
- [十一、运行时安全与进程级攻击](references/split-12-section.md)
- [十二、云原生 AI 攻击面](references/split-13-ai.md)
- [十三、AI 大模型结合攻防（LLM 辅助安全测试）](references/split-14-ai-llm.md)
- [十四、工具链](references/split-15-section.md)
- [十五、测试检查清单](references/split-16-section.md)
- [十六、修复建议](references/split-17-section.md)
- [十七、注意事项与合规声明](references/split-18-section.md)
- [真源](references/split-19-section.md)
- [外部库增量（2026-10-11 分享包）](references/split-20-2026-10-11.md)
- [三点五、实战：容器内命令执行到手后的天花板判定（15 分钟止损）](references/split-21-15.md)
- [三条容器/虚拟化逃逸面（研究 PoC，本机未复现）](references/split-22-poc.md)
