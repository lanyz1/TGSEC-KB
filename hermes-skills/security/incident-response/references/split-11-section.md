## 十、云与容器事件响应专项

### 10.1 云日志源映射（必须双平面采集）
| 组件 | AWS | Azure | GCP |
|------|-----|-------|-----|
| 云API调用 | CloudTrail | Activity Logs | Cloud Audit Logs |
| 托管K8s控制面 | EKS控制面日志 | AKS诊断日志 | GKE审计日志 |
| 网络流 | VPC Flow Logs | NSG Flow Logs | VPC Flow Logs |
| 身份/IAM | CloudTrail IAM事件 | Entra ID(Azure AD)日志 | Cloud IAM审计 |
| 负载均衡 | ALB/NLB访问日志 | Application Gateway | Cloud Load Balancing |
| DNS | Route 53查询日志 | Azure DNS分析 | Cloud DNS日志 |

**两平面原则**：平面1=VM内证据（SSH采集/磁盘快照）；平面2=云审计追踪（API调用/IAM变更/安全组修改）。
攻击者在云侧的活动（如修改安全组、创建新用户）从 VM 内部永远看不到——**两平面都要采**。

### 10.2 云取证与响应
```bash
# 云磁盘快照（VM证据，先于登录VM操作——快照不产生VM内污染）
# AWS EBS
aws ec2 create-snapshot --volume-id vol-xxxx --description "IR-$(date)"
# Azure 磁盘
az snapshot create -g rg -n snap1 --source disk1
# GCP
gcloud compute disks snapshot disk-1 --zone=us-central1-a

# 云审计日志采集
aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=admin --start-time 2026-06-27
az monitor activity-log list --start-time 2026-06-27
gcloud logging read 'protoPayload.authenticationInfo.principalEmail="<EMAIL-REDACTED>"' --limit=1000

# 响应动作
# 轮换泄露的AK/SK（立即生效，勿只禁用IAM用户）
aws iam create-access-key --user-name compromised-user   # 先建新key再删旧key
# 撤销角色AssumeRole链、删除异常安全组规则
# 云主机先打快照再隔离（云上"拔网线"=安全组deny-all或停止实例）
```

### 10.3 容器取证（易逝性最高，采集优先级第一）
```
容器是易失的：pod重建/镜像回收会秒杀证据——先采集再调查
采集顺序：
1. kubectl logs <pod> --previous        # 崩溃前日志（攻击导致重启时是关键）
2. kubectl describe pod <pod>           # 事件与配置
3. kubectl get pod <pod> -o yaml        # 保存Pod规格
4. 容器文件系统diff：docker diff <container> 或 overlay层差异
5. 容器内进程与网络：kubectl exec 或 宿主机 nsenter（优先用静态编译工具）
6. 镜像保全：docker save <image> -o image.tar 或 skopeo copy
7. 容器内存：宿主机上 avml --pid <容器内进程PID>（在宿主机PID空间可见）
8. 卷快照：CSI快照（EBS snapshot / gcloud compute disks snapshot）
9. 运行时取证：crictl logs / crictl inspect（containerd运行时）
10. 网络：宿主机 tcpdump -i any 过滤 pod IP；Cilium 下 hubble observe
```

### 10.4 Kubernetes 事件响应（前60分钟清单）
```
0-15分钟：
  kubectl cordon <node>                          # 封锁受影响节点
  kubectl label ns <ns> network-policy=deny       # 或直接下发deny-all NetworkPolicy
  采集：kubectl logs --previous、node卷快照、容器内存、网络连接
15-30分钟：
  导出审计日志（RequestResponse级才能看到exec内容）
  复制容器可写层、保全Pod规格
30-45分钟遏制：
  轮换被攻陷ServiceAccount令牌、撤销可疑RBAC绑定
  kubectl drain <node>（证据采集完成后）
  云防火墙封禁恶意IP
45-60分钟：
  通知指挥与利益相关方、更新事件工单、界定爆炸半径

检测工具：Falco/Tetragon（运行时syscall检测）、tracee-ebpf、Sysdig Inspect
审计日志：kube-apiserver audit policy 配置 RequestResponse 级别记录 exec/attach/portforward
  配置开启前无法回溯——把"审计策略配置"当作IR计划的一部分
安全上下文基线：容器以非root运行、seccomp/AppArmor、只读rootfs、限制特权容器
常见事件类型：容器逃逸、暴露API Server、ServiceAccount滥用、恶意镜像（供应链）
```

### 10.5 云身份与凭据事件
```
2026 云入侵主流路径：泄露AK/SK、OAuth应用滥用、云服务账号横向
响应重点：
1. 立即轮换（先建新再删旧，避免业务中断）
2. 审计 IAM 变更历史（谁在何时加了什么权限）
3. 检查：存储桶策略是否被改（公开读写）、函数/容器是否被注入后门
4. 计费异常（挖矿/资源消耗爆炸）也是重要信号
5. 云凭据扫描：GitHub/公开仓库泄露检测（trufflehog）
```

