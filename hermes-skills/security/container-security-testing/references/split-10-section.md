## 九、命名空间隔离与网络策略/服务网格绕过

### 9.1 K8s 默认网络模型与 NetworkPolicy 绕过

```
核心事实：
- K8s 默认"全通"：无 NetworkPolicy 时任意 Pod 可访问任意 Pod（跨 namespace）
- NetworkPolicy 依赖 CNI 实现：Flannel(非混合模式) 不支持 → 策略形同虚设
- Calico/Cilium/Antrea 才真正执行策略；先确认 CNI 类型
```

```bash
# 确认 CNI 与策略执行能力
kubectl get pods -n kube-system | grep -E "calico|cilium|flannel|antrea|weave"
kubectl get networkpolicies -A                     # 检查是否真的存在策略
kubectl get networkpolicies -A | wc -l             # 0 = 全网全通

# 测试隔离是否生效（Pod A → Pod B）
kubectl exec <pod-a> -- wget -qO- -T 2 http://<pod-b-ip>:80 && echo "OPEN（策略未生效）"
```

**NetworkPolicy 绕过思路：**
```
1. hostNetwork Pod 绕过策略（直接走宿主网络栈，多数策略不覆盖节点网络）
2. NodePort 访问：通过节点 IP:NodePort 直连（绕过基于 Pod 的 Ingress 策略）
3. 标签伪造：策略按 label 选择器匹配，Pod 打上目标 label 即可被放行（若有创建/修改 Pod 权限）
4. IP 白名单绕过：策略仅限制 podSelector，未限制 ipBlock → 从外部/节点侧访问
5. 策略未覆盖的协议：DNS（53）常被放行 → 走 DNS 隧道；部分策略漏掉 ICMP/UDP 高端口
6. kube-proxy 直连：ClusterIP 后实际流量到 NodePort → 绕过 L4 策略边界
```

### 9.2 服务网格（Istio/Linkerd/Cilium）绕过

```bash
# 服务网格安全特性（防御视角）：
# - mTLS：自动双向 TLS（默认 permissive 模式 = 兼容明文，需切 STRICT）
# - AuthorizationPolicy：L7 细粒度（HTTP method/path/JWT）
# - PeerAuthentication：mTLS 模式控制

# 绕过测试点：
# 1. permissive mTLS：明文流量被接受 → 直接非网格流量访问（绕过身份校验）
# 2. 非注入 Pod：未注入 sidecar 的 Pod 不受 AuthorizationPolicy 约束（策略只作用于代理）
# 3. 直接访问 Service IP 绕过 sidecar（如果策略只校验来源 label）
# 4. CiliumNetworkPolicy 与 NetworkPolicy 双栈不一致：只测了原生 NP 没测 CiliumPolicy
# 5. 网格内 SSRF：Pod 间 SSRF 借高权服务身份访问受限目标
```

```bash
# 测试 mTLS 是否强制（STRICT）
kubectl exec <pod-a> -- sh -c "wget -qO- -T 2 http://<service>:<port>/" 
# 若明文可达 → permissive 或未强制执行
kubectl get peerauthentication -A
```

### 9.3 服务网格/ingress 组件攻击面

```
- ingress-nginx 配置注入系列（2025-2026 持续爆发，全部可 RCE/窃取 Secret）：
  CVE-2025-1974（admission controller RCE 提权）、CVE-2026-3288（rewrite-target）、
  CVE-2026-1580（auth-method）、CVE-2026-24512（rules.http.paths.path）、
  CVE-2026-24513（auth-url 保护绕过）、CVE-2026-24514（admission DoS）、
  CVE-2026-4342（comment 配置注入）、CVE-2025-15566（auth-proxy-set-headers）
  根因：annotation 中的 nginx 配置注入（rewrite-target/auth-url/load_module 等）
- 测试：提交带恶意 annotation 的 Ingress 对象 → 触发 nginx 配置生成 → 注入指令
- 缓解：Ingress 注解白名单（Kyverno）、限制 Ingress 控制器 RBAC（仅读自己 namespace Secret）
```

