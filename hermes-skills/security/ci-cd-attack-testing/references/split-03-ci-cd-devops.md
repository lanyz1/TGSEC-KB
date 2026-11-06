## 一、CI/CD 攻击面全景（DevOps 供应链攻击链）

### 1.1 现代 CI/CD 流水线架构
```
开发者终端 → 代码托管平台(GitHub/GitLab/Gitee)
              ↓ push / PR / webhook
         CI 系统(Jenkins/GitHub Actions/GitLab CI/TeamCity)
              ↓ 构建+测试+扫描
         制品仓库(Nexus/Artifactory/npm/PyPI/Docker Registry/Harbor)
              ↓ 拉取制品
         CD/发布平台(ArgoCD/Spinnaker/Flux/Helm)
              ↓ 部署
         云/集群环境(K8s/AWS/Azure/阿里云) → 生产应用
```
**关键特征**：每一环都**自动信任**上一环的输出（代码→构建产物→部署），且各环节通常持有通往下一环的高权限凭据——这正是供应链攻击的价值放大器。

### 1.2 攻击面分层模型
| 层次 | 组件 | 红队价值 |
|------|------|---------|
| L1 开发者层 | 开发者终端/IDE/Git凭据/浏览器会话 | 初始入口、上游凭据 |
| L2 代码库 | GitHub/GitLab/Gitee 仓库/分支/PR/Webhook | 源码+Secret+影响力 |
| L3 CI层 | Jenkins/GitHub Actions/GitLab CI/TeamCity | **构建凭据+RCE**（最高价值） |
| L4 制品层 | Nexus/Artifactory/npm/PyPI/Docker Registry/Harbor | 供应链投毒点 |
| L5 发布层 | ArgoCD/Flux/Helm/Spinnaker | 直达生产的开关 |
| L6 运行层 | K8s/云平台/生产应用 | 最终目标 |

### 1.3 信任边界与攻击链模型
```
# 攻击者只需要突破任意一个信任边界：
# 1) 写代码库（恶意代码/依赖投毒）→ 下游自动构建 → 自动部署 → 生产沦陷
# 2) 攻 CI 平台（RCE/凭据）→ 拿到全部部署凭据 → 直接控制生产
# 3) 攻制品库（篡改制品）→ 所有拉取该制品的环境被动感染
# 4) 攻 CD 平台（ArgoCD 等）→ 一键把恶意工作负载部署到集群
# 5) 攻开发者终端（凭据/插件）→ 冒充开发者提交恶意代码
# 决策树：哪个环节暴露面最大、防护最弱、下游影响最广，就优先打哪个
```

### 1.4 目标优先级评估（红队决策）
```
# 评估维度：可达性 × 权限放大倍数 × 下游影响范围
# 高优先级：
#   - 暴露到公网的 CI 平台（Jenkins/GitLab Runner）——直接 RCE 面
#   - 无鉴权/弱口令的制品库与 ArgoCD——直通生产
#   - 自托管 Runner（GitHub Actions）——等于集群内高权限 pod
#   - 大型开源/内部公共仓库——供应链影响面大
# 中优先级：内部代码库、开发者机器
# 每攻陷一环，立即收集"通往下一环的凭据"（deploy key/CI token/云凭据）
```

