## 三、合规即代码与策略引擎

### 3.1 OPA 策略示例
```rego
# K8s Pod 安全策略
package kubernetes.admission

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("容器 %v 不允许使用特权模式", [container.name])
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.securityContext.runAsNonRoot
    msg := sprintf("容器 %v 必须以非root运行", [container.name])
}
```

### 3.2 CIS Benchmark 自动化
```bash
# Docker CIS Benchmark
docker-bench-security

# K8s CIS Benchmark
kube-bench

# AWS CIS Benchmark
prowler --checks cis

# 云安全态势（GCP/Azure）
# scoutsuite / pacu 组合
```

### 3.3 策略引擎选型与进阶
| 引擎 | 语言 | 适用 |
|------|------|------|
| OPA/Gatekeeper | Rego | 云原生准入 + 通用策略 |
| Kyverno | YAML | K8s 原生，学习成本低 |
| Conftest | Rego | 通用配置测试（Dockerfile/Terraform/K8s 均可） |
| HashiCorp Sentinel | Sentinel | Terraform Enterprise 集成 |

```bash
# Conftest 测试任意配置
conftest test deployment.yaml -p policies/
```

### 3.4 策略生命周期管理
- 策略即代码：存放在独立 `security-policies` 仓库，走 MR 评审 + 单测（OPA 单元测试 `opa test`）
- 变更灰度：先在**告警模式**（audit）运行新策略，观察误报，再切换**强制模式**（enforce）
- 版本化与回滚：策略与集群/环境版本绑定，回滚策略如同回滚代码

