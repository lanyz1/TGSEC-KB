## 十三、AI 大模型结合攻防（LLM 辅助安全测试）

### 13.1 AI 辅助 K8s 配置审计（LLM 找权限）

```
核心用法：把集群配置喂给 LLM，让模型像资深审计师一样交叉分析权限与攻击路径。

场景1 RBAC 分析：导出全部 Role/ClusterRole/Binding → 让 LLM 输出：
  - 每个 SA 的可利用提权链（对照第六章六大链）
  - cluster-admin 绑定的非预期主体
  - 通配符权限、secrets get、nodes/proxy、impersonate 等危险项
场景2 NetworkPolicy 审计：导出 NP + 服务清单 → LLM 检查：
  - 是否存在无策略保护的高价值服务（数据库/管理端）
  - 默认全通 namespace、跨 namespace 意外放行
  - 策略与 CNI 能力是否匹配（Flannel 无 NP 实现）
场景3 镜像/Dockerfile 审计：LLM 静态扫描 Dockerfile 找密钥/高危指令/供应链风险
场景4 审计报告生成：汇总发现 → 按 CVSS/攻击链位置排序 → 生成可执行修复清单
```

```bash
# 数据导出命令（供 LLM 分析）
kubectl get role,rolebinding,clusterrole,clusterrolebinding -A -o json > rbac.json
kubectl get networkpolicy -A -o json > netpol.json
kubectl get sa -A -o json > sa.json
kubectl get secrets -A -o json > secrets.json
# 提示词模板（关键）：扮演资深 K8s 红队，基于以下 RBAC 数据列出所有可到达 cluster-admin
# 的提权链，按可行性排序，标注所需权限与步骤：
# （粘贴 rbac.json 中与 <namespace>/<sa> 相关的条目）
```

### 13.2 AI 驱动集群攻击路径规划

```
- 自动枚举：LLM Agent 调用 kubectl/kube-hunter/kubescape 输出，迭代式提出下一步
- 攻击图生成：把 RBAC/网络/逃逸路径输入 LLM → 生成完整攻击图（节点=权限，边=动作）
- 红队 Copilot：结合 kube-hunter、peirates、boopkit 等工具输出，LLM 归纳当前阶段
  与最优下一步（如"检测到 secrets get → 建议枚举 kube-system 高权 SA → 链1 提权"）
- 检测规避建议生成：LLM 基于已选攻击路径提示审计日志规避点与工具特征清理
- 注意：LLM 输出需人工复核（防止幻觉命令/无效 payload），payload 一律先本地验证
```

### 13.3 容器化 AI 应用自身攻击面（防御与测试双视角）

```
- 提示注入/越狱：容器化 LLM 服务未做输入过滤 → 系统提示泄露/工具滥用
- RAG 投毒：向量库未授权写入 → 检索结果被污染 → 业务决策被操纵
- 模型窃取：未认证 /api/push 或模型文件下载 → 知识产权泄露
- 训练/微调供应链：拉取恶意 HuggingFace 模型（权重后门、pickle 格式 RCE——
  PyTorch .pth/safetensors 加载链，攻击面与反序列化类似）
- AI Agent 权限放大：Agent 持有的 K8s/云凭据被提示注入劫持 → 以 Agent 身份执行高危操作
- 检测（防御视角）：推理服务器视为互联网边缘资产（紧急补丁 SLA）、管理 API 强制认证、
  出网白名单、SCA 覆盖、eBPF 运行时行为监控（如 DeSFAM：VAE+iForest 系统调用异常检测）
```

