# 零信任 / ZTNA / 微隔离：审计与绕过速查（进攻视角）

> 本文覆盖：零信任三平面、ZTNA 身份感知代理配置要点、WireGuard/Tailscale 真实命令、K8s NetworkPolicy/Calico 微隔离、kube-bench/RBAC 审计，以及**东西向盲区与 mTLS 失效点**。
> 与 `iam-pam-ops.md` 分工：身份面（IdP/SSO/MFA/PAM/云 IAM）在那里，网络与代理面在这里。
> 命令标注：无标注 = 上游原样或已对照官方文档核对；`（未验证）` = 未核对具体语法。仅限授权范围。

## 1. 零信任三平面与决策点（NIST SP 800-207，上游摘要）

| 平面 | 内容 | 可攻击/可审计的位置 |
|:---|:---|:---|
| 身份 | user/group/role/clearance，SSO 会话 | 策略里的通配组、排除名单、NameID 可预测（见 iam-pam-ops.md） |
| 设备 | 托管/合规/EDR 状态/补丁版本 | 设备姿态"仅上报不校验"、BYOD 例外、posture 服务不可达时 fail-open |
| 网络 | 分段/微隔离/SDP 覆盖层 | 东西向无策略、覆盖层外的旁路路径（本文重点） |

七原则（上游摘要）：无论网络位置所有通信都必须加密；访问按会话逐次授权；基于动态策略（用户/设备/环境上下文）决策；PDP（策略决策点）与 PEP（策略执行点）分离。落地检查点：**PEP 是否全覆盖**（每个入口都有代理/网关，而不是只保护 Web）、**策略是否 default-deny**、**上下文是否真被校验**（设备姿态/地理位置只上报不判断 = 形同虚设）。

## 2. ZTNA 身份感知代理：配置要点与绕过面

### 2.1 Cloudflare Access（上游原样命令）
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64 && sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
cloudflared tunnel login && cloudflared tunnel create company-app-tunnel && cloudflared tunnel route dns company-app-tunnel app.company.com
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: company-app-tunnel
credentials-file: /home/user/.cloudflared/company-app-tunnel.json
ingress:
  - hostname: app.company.com
    service: http://localhost:8080
  - hostname: admin.company.com
    service: http://localhost:9090
  - service: http_status:404
EOF
cloudflared tunnel run company-app-tunnel
# Access 策略（API）
curl -X POST https://api.cloudflare.com/client/v4/accounts/<account-id>/access/policies \
  -H "Authorization: Bearer $CF_TOKEN" \
  -d '{"name":"Internal App Access","decision":"allow",
       "include":[{"email":{"email":"<EMAIL-REDACTED>"}}],
       "require":[{"device_posture":{"integration_uid":"<uid>","type":"warp"}}]}'
# WARP 设备客户端
curl -fsSL https://pkg.cloudflareclient.com/cloudflare-warp.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-warp.gpg && sudo apt-get install cloudflare-warp && warp-cli register && warp-cli set-license <license> && warp-cli connect
# 校验 Access 签发的 JWT（网关/后端应做的事）：头 Cf-Access-Jwt-Assertion / Cookie CF_Authorization
curl -s https://<team>.cloudflareaccess.com/cdn-cgi/access/certs | jq '.keys[]|{kid,alg}'   # JWKS
```
绕过/审计点：① **应用存在可直连的源站 IP/端口**（隧道只是其中一条入口）= 最彻底的绕过，用测绘引擎找源站；② 策略 `Include: Everyone`、邮箱域通配（`@gmail.com`）、只验邮箱不验组 → 任何持邮箱者进内网；③ **Service Token 泄露**（`CF-Access-Client-Id`/`CF-Access-Client-Secret` 常写死在 CI/脚本里）→ 免身份直连；④ 路径级策略未做规范化（`/admin`、`/admin/`、`/admin/..;/`、大小写、URL 编码、`X-Original-URL` 类头的差异）→ 用等价路径命中受保护路由；⑤ 只在网关校验身份、后端信任 `Cf-Access-*` 头 → 一旦能直连源站即可伪造该头；⑥ 未保护资产路径（静态桶、`/cdn-cgi/`、备用域名）。

### 2.2 Zscaler ZPA / Appgate SDP 配置检查点（无公开 CLI，按控制台要点核对）
- ZPA：**App Connector 组**是否部署在可全域访问的网段（等于"小号 VPN"）；**Server Groups** 定义过宽（整个 `/16`、通配域名）→ 授权一个应用即触达整段；**Access Policy** 依赖的 SAML 属性映射是否可从用户侧篡改（自助属性/组名前缀通配）；**Client Connector** 是否允许旁路（客户端未装或断开后仍能走内网路由）；Private Service Edge 位置与信任链。
- Appgate SDP：Entitlements 粒度（是否 `0.0.0.0/0`）、Conditions（Site/Device/时间窗）是否真被执行、Device Scripts 版本、**Client 强制**程度；未装客户端的同网段主机可直接访问被保护资源（in-band 代理未覆盖）即绕过。
- 通用验收：**逐条问"有没有不经代理的路径"**——同网段、VPN 旁路、跳板机、CI runner、K8s NodePort、数据库直连、备份网段。

## 3. WireGuard / Tailscale 真实命令

```bash
sudo apt-get install wireguard
wg genkey | tee private.key | wg pubkey > public.key && wg genpsk > preshared.key
cat > /etc/wireguard/wg0.conf << 'EOF'
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>
[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.0.0.2/32
EOF
wg-quick up wg0 && systemctl enable wg-quick@wg0
wg show && wg show wg0 dump && sudo wg showconf wg0     # 审计：对端、最新握手、AllowedIPs 全量、传输量
curl -fsSL https://tailscale.com/install.sh | sh        # Tailscale = 基于 WireGuard 的 SDP
sudo tailscale up --authkey tskey-auth-xxxx --advertise-routes=10.10.0.0/16 --accept-routes --ssh && tailscale status --json
tailscale whois 100.64.0.1                             # 反查 IP→身份（ACL 是否真生效）; tailscale ping <node> && tailscale lock status   # 连通性 + tailnet lock（防设备注入）
```
审计点：① `AllowedIPs = 0.0.0.0/0`（全流量隧道）+ 客户端间的 `AllowedIPs` 允许互访 → 节点即横向通道；② 只有共享密钥/长期 authkey，无设备姿态、无 SSO 有效期 = 拿到配置即长期访问；③ Tailscale ACL 只能在管理控制台/HTTP API 修改（CLI 无 acl 子命令，未验证），因此**审计重点是导出 ACL 后查 `dst: ["*:*"]` 与 `tagOwners` 过宽**（上游 ACL hujson 示例：`{"action":"accept","src":["tag:ops"],"dst":["*:*"]}` 就是全域放行）；④ `--advertise-routes` 让单节点成为子网路由器 → 该节点被打穿即整段暴露。

## 4. 微隔离：K8s NetworkPolicy 与 Calico

```yaml
# 纯 K8s：默认拒绝（注意：需 CNI 支持策略，flannel 默认不执行）
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny-all, namespace: production }
spec: { podSelector: {}, policyTypes: [Ingress, Egress] }
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-frontend-to-api, namespace: production }
spec:
  podSelector: { matchLabels: { app: api-server } }
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector: { matchLabels: { role: frontend } }   # 命名空间必须已有 role=frontend 标签，否则规则静默失效
    ports: [{ protocol: TCP, port: 8080 }]
```
```yaml
# Calico（上游原样结构）：全局默认拒绝 + 命名空间间放行
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata: { name: security.default-deny }
spec: { selector: "all()", types: [Ingress, Egress] }
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata: { name: allow-frontend-to-api, namespace: production }
spec:
  selector: "app == 'api-server'"
  ingress:
  - action: Allow
    protocol: TCP
    source: { namespaceSelector: "role == 'frontend'" }
    destination: { ports: ['8080'] }
```
```bash
kubectl apply -f <policy>.yaml && kubectl get networkpolicy -A && kubectl describe networkpolicy -n production
kubectl create -f https://docs.projectcalico.org/manifests/tigera-operator.yaml     # 上游原样：安装 Calico
calicoctl get globalnetworkpolicy -o yaml && calicoctl get networkpolicy -A -o yaml && calicoctl apply -f <policy>.yaml && calicoctl node status
calicoctl get felixconfiguration default -o yaml    # 关注 defaultEndpointToHostAction / policy 是否真启用
kubectl get ippools.crd.projectcalico.org -o yaml  # IP 池是否覆盖全集（未覆盖的网段=策略盲区）
```
审计点：① 策略只写 `Ingress` 不写 `Egress`（默认出站放行）→ 横向与 C2 外联无阻；② 选择器写错标签 → 静默失效（`kubectl get ns --show-labels` 核对）；③ CNI 不支持策略或策略未落到所有节点（Calico 的 policy 依赖 Felix 正常，`calicoctl node status` 看 BGP）；④ 只保护 pod 间流量，不覆盖 `hostNetwork` pod、NodePort、`169.254.169.254`（云元数据）、CoreDNS、kubelet:10250。

## 5. K8s 加固与 RBAC 审计命令

```bash
kube-bench run --targets master,node,etcd,policies     # CIS 基准：master/node/etcd/策略四类
kubectl apply -f job.yaml && kubectl logs kube-bench-j76s9        # 集群内跑（需 hostPID 与宿主目录）
kube-bench run --targets master --json --outputfile /tmp/kb.json ; ./kube-bench --config-dir cfg --config cfg/config.yaml   # JSON 归档；后者为上游原样（源码方式运行）
kubectl auth can-i list pods --as=system:serviceaccount:security-demo:app-sa
kubectl auth can-i delete pods --as=system:serviceaccount:security-demo:app-sa
kubectl auth can-i create deployments --as=system:serviceaccount:security-demo:app-sa
kubectl auth can-i --list --as=system:serviceaccount:security-demo:app-sa     # 全权限清单（审计最快入口）
kubectl get rolebindings --all-namespaces -o yaml | grep "delete"            # 上游原样：找越权绑定
kubectl get clusterrolebindings -o yaml | grep -A5 "secrets"                 # 上游原样
kubectl get clusterrole -o yaml | grep '"*"' -B5                             # 通配权限
for crb in $(kubectl get clusterrolebindings -o name); do role=$(kubectl get $crb -o jsonpath='{.roleRef.name}'); kubectl describe clusterrole $role 2>/dev/null | grep -q "secrets" && echo "Risk: $crb can access secrets"; done
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} hostNetwork={.spec.hostNetwork} hostPID={.spec.hostPID} automount={.spec.automountServiceAccountToken}{"\n"}{end}'
kubectl get sa -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'   # 谁有 SA（配合上一条找可挂载 token 的 pod）
```
审计点：① `cluster-admin` 绑定到 SA（上游给出的风险模式）；② ClusterRole 含 `*`/`secrets`/`pods/exec`；③ `automountServiceAccountToken` 默认 true → 任何 pod 被拿下即拿 token；④ NodePort/`hostNetwork`/特权容器绕过网络策略；⑤ 审计日志（`--audit-policy-file`）是否开了 `RequestResponse` 级别（默认可能只 Metadata）。

## 6. 微隔离与 SDP 的绕过/审计面（东西向盲区清单）

1. **南北向看得见、东西向看不见**：入口 WAF/代理有日志，pod 间、VPC 内、跨账号对等连接流量默认无策略（K8s 无 NetworkPolicy = allow-all）；
2. **默认策略缺失/只写一半**：只 Ingress 无 Egress；只保护 web 端口，漏 SSH/RPC/数据库端口与 UDP；
3. **覆盖层外的主机**：`hostNetwork`/NodePort、kubelet 10250、etcd 2379、云元数据 169.254.169.254、CoreDNS、备份与管理网段、CI runner；
4. **Service Mesh mTLS 失效点**：Istio 默认 `PeerAuthentication: PERMISSIVE` —— 官方明确"PERMISSIVE 下明文流量**默认不做任何认证/授权校验**"，只有 STRICT 才能阻止绕过 mesh 的连接；`istio-injection=disabled` 的命名空间/未注入 pod 直接明文访问被保护服务；sidecar 只接管 TCP（UDP 直通）；init/主机级组件不经 sidecar；mesh 外客户端无 mTLS 但可能被放行；
5. **审计命令**（已核对）：
```bash
kubectl get peerauthentication --all-namespaces
kubectl get peerauthentication default -n istio-system -o jsonpath='{.spec.mtls.mode}'   # PERMISSIVE = 明文放行
kubectl get peerauthentication -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} {.spec.mtls.mode} {.spec.portLevelMtls}{"\n"}{end}'
istioctl x authz check <pod>            # 直接看 Envoy 里生效的 AuthorizationPolicy（含 mesh/ns/workload 合并结果）
istioctl x describe pod <pod.foo>       # 含生效的 PeerAuthentication 与 mTLS 模式; istioctl proxy-config cluster <pod.foo> | grep -i <target>   # 目标是否走 mTLS
```
6. **SDP 侧**：SDP 只保护"经控制器的连接"→ 直连内网 IP/端口、同网段主机、App Connector 自身所在网段都可绕过；Connector 是内网跳板，其凭据/配置泄露等于内网立足点。

## 7. 参考
- `iam-pam-ops.md`：IdP/SSO/MFA/PAM/云 IAM 侧。
- 上游：`36-零信任架构-ZeroTrust/skills/*`（零信任设计/ZTNA 集成/微隔离与 SDP）、`33-容器安全-ContainerSecurity/skills/Kubernetes RBAC与安全策略.md`。
- 本库相关：`cloud-k8s`、`container-security-testing`、`ip-ban-bypass`、`cloudflare-bypass`、`internal-tunnel`。
