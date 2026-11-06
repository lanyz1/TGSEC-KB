<!-- archived from /root/.hermes/skills/security/enterprise-iam-pam-zerotrust/SKILL.md on 2026-10-21 -->

---
name: enterprise-iam-pam-zerotrust
description: "Use when 打IAM/PAM/零信任:Vault、SSO断言、MFA弱面、微隔离。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/enterprise-iam-pam-zerotrust`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/enterprise-iam-pam-zerotrust/…')`，不要相对 `references/legacy/` 解析。

# 企业 IAM / PAM / 零信任：审计与绕过

## 何时用
- 目标有企业身份设施：Okta/Entra ID/Keycloak/PingFederate、SAML 2.0 或 OIDC SSO、MFA、SCIM 供应。
- 见到 PAM/特权访问组件：HashiCorp Vault、CyberArk（PVWA/PSM/CPM/AIM/PTA）、Teleport、卓豪等堡垒机。
- 见到零信任/微隔离组件：Cloudflare Access、Zscaler ZPA、Appgate SDP、WireGuard/Tailscale 覆盖网、Istio/Linkerd mTLS、Calico/Cilium NetworkPolicy。
- 诉求是"能不能进后台/能不能横向/身份面有没有漏"：默认配置弱点、SSO 与 JIT 绕过面、身份感知代理与微隔离的审计/绕过面。

## 不适用（交给别的卡）
- AD 域攻击链（Kerberoasting/ADCS/委派/DCSync/横向移动/接管）→ `windows-ad-pentest`、`active-directory`、`account-takeover-chain`。
- 应用层越权与对象级授权（IDOR/BOLA/对象矩阵）→ `object-matrix-authz`、`api-authz-idor-testing`。
- 单纯 JWT 算法/密钥问题 → `jwt-attacks`；OAuth 流程问题 → `oauth-oidc-flow`；OTP 爆破细节 → `2fa-otp-bypass`。
- 容器/K8s 逃逸与云原生横向 → `cloud-k8s`、`container-security-testing`。

## 工作流
1. **识别面**：SSO 端点（`/.well-known/openid-configuration`、`/saml/metadata`、`/app/metadata`）、MFA 方法、PAM 入口（Vault `sys/health`、Teleport `:3080`、CyberArk PVWA）、零信任代理指纹（cloudflared/Access 头、ZPA 客户端、Tailscale 域名）。
2. **取配置**：低权身份优先。Vault `auth list -detailed`/`sys/mounts`；IdP 元数据与 JWKS；K8s `auth can-i --list`；Calico/Netpol 全量导出；Mesh `PeerAuthentication` 全量导出。
3. **找默认弱点**：先不用漏洞，用"默认/缺省"三件套——策略为空（无速率限制、无 Egress 策略、无 STRICT mTLS）、绑定过宽（`*:*`、`node_labels=*`、`Include: Everyone`）、旁路存在（直连源站、本地账号、hostNetwork、非注入命名空间）。
4. **验证绕过**：每条绕过都要有可复现证据（请求/命令 + 响应），限速类要给出计数与时间戳区间；不要以"配置看起来不安全"结案。
5. **回收面审计**：离职/旧 IdP/refresh token/API key/设备证书/活跃会话；这是客户最常问且最易出成果的一侧。

## 命令速查（细节见 references/）
```bash
# Vault：枚举与 JIT 面
vault auth list -detailed ; vault read sys/mounts ; vault token capabilities <token> database/creds/readonly
vault list sys/leases/lookup/database/creds/readonly/ ; vault lease revoke -prefix database/creds/readonly
vault audit list -detailed        # 空 = 取凭据无日志（关键结论）
# PAM：Teleport JIT 与录制
tsh ls ; tsh ssh -L 5432:localhost:5432 ops@db-01 ; tsh request create --roles=<role> --reason "P1 #1234" ; tsh play <id>
# SSO：断言字段与验签
curl -s https://idp/.well-known/openid-configuration | jq . ; curl -s https://idp/.well-known/jwks.json | jq '.keys[]'
echo "$SAMLResponse" | base64 -d | xmllint --format - ; openssl x509 -in idp.crt -noout -fingerprint -sha256
# MFA：限速与防护开关
kcadm.sh get realms/myrealm | jq '{bruteForceProtected,failureFactor,permanentLockout}'
az rest --method get --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies"
# 云 IAM：宽策略与信任面
aws iam get-role --role-name X --query 'Role.AssumeRolePolicyDocument' ; aws iam get-account-summary
gcloud projects get-iam-policy <p> --flatten="bindings[].members" --filter="bindings.role:roles/owner" --format=table
az role assignment list --all --include-inherited -o table
# 零信任/微隔离
kubectl get networkpolicy -A -o yaml ; calicoctl get globalnetworkpolicy -o yaml ; kubectl get peerauthentication -A
wg show ; tailscale status --json ; cloudflared access ssh --hostname <host>
kube-bench run --targets master,node,etcd,policies ; kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>
```

## 验收判据（结案前自问）
- 每条"绕过"都要有**可复现证据**：命令 + 时间 + 响应原文；配置类结论（如"无速率限制"）需给出连打计数与时间戳区间，不能只贴配置片段。
- 区分三级：**已验证**（自己成功绕过）／**未验证**（只看到弱配置）／**不适用**（组件存在但不在 scope）；报告里必须标级。
- 结论必须能回答"最短路是什么"：从任一低权起点到目标权限的最短链（含旁路路径：直连源站/本地账号/hostNetwork/非注入命名空间）。

## Pitfalls
- **PERMISSIVE 误判**：Istio 默认 PERMISSIVE 时明文流量不做认证/授权校验；只看到 mTLS 存在就判"已加密受保护"是错的——必须查 `PeerAuthentication` 模式与 `istioctl x authz check`。
- **只测南北向**：入口 WAF 代理全通不代表内部隔离；东西向与 Egress 常无策略（无 NetworkPolicy = allow-all）。
- **只验单一路径**：Access/网关只保护已知主机名，未保护资产路径（静态桶、`/cdn-cgi/`、旧域名）、可直连源站 = 结论作废。
- **策略写了但静默失效**：NetworkPolicy 的选择器标签不存在（命名空间未打标签）、CNI 不支持策略、Calico Felix 未正常 → 看起来有策略实际全放行，必须用实际连通性验证。
- **拿 JIT 当已加固**：`secret_id_ttl=0`、`max_ttl` 24h+、`session_recording=off`、`max_session_ttl` 数十小时都会把 JIT 变长期访问。
- **不区分 IdP 停权与应用停权**：IdP 禁用后下游本地账号/长期 refresh token/API key 仍活，需逐一验。
- **越界**：所有命令仅限授权目标；凭据走环境变量/保险库注入；爆破类先确认许可并控速。

## 参考文件
- `references/iam-pam-ops.md`：Vault 部署/JIT/动态凭据/租约、CyberArk+Teleport、SAML/OIDC 字段与错误配置、MFA 弱面、身份生命周期、AD 审计、云 IAM 审计。
- `references/zerotrust-ztna-microseg.md`：三平面、Cloudflare Access/ZPA/Appgate、WireGuard/Tailscale、NetworkPolicy/Calico、kube-bench/RBAC、东西向盲区与 mTLS 失效点。
- `references/provenance-and-unverified.md`：上游吸收/丢弃明细与命令来源（原样搬运 vs 补充 vs 更正）。
