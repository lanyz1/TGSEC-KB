# REPORT — enterprise-iam-pam-zerotrust 抽取报告

产出：`references/iam-pam-ops.md`（220 行，上限 220）、`references/zerotrust-ztna-microseg.md`（160 行，上限 160）、`DRAFT-SKILL.md`（正文 64 行，上限 120）。
上游只读，未修改任何上游文件。所有命令按「可照敲」标准写入；未核对者均显式标 `（未验证）`。

## 1. 读取清单（上游，只读）

| 文件 | 体量 | 处置 |
|:---|:---|:---|
| `32-身份访问管理-IAM/skills/企业IAM策略与架构-EnterpriseIAMStrategy.md` | 13,789 字符 | 吸收（IAM 架构、Keycloak CLI） |
| `32-…/PAM特权账号管理-PrivilegedAccessManagement.md` | ~15k 字符 | 吸收（Vault/CyberArk/Teleport 主体） |
| `32-…/云IAM与联邦认证-CloudIAMFederation.md` | ~13.5k 字符 | 吸收（AWS/GCP/Azure 审计命令） |
| `32-…/AD域安全与攻击路径分析-ADSecurityAttackPathAnalysis.md` | 9,884 字符 | **部分吸收**：只取审计命令（PingCastle/auditpol/PowerView） |
| `32-身份访问管理-IAM/README.md` | — | 仅确认目录结构 |
| `36-零信任架构-ZeroTrust/skills/零信任架构设计与实施-ZeroTrustArchitectureDesign.md` | 9,078 字符 | 吸收（三平面、NIST 七原则、PDP/PEP） |
| `36-…/ZTNA解决方案与IAM集成-ZTNASolutionsIAMIntegration.md` | 10,161 字符 | 吸收（cloudflared/Access/ZPA/Appgate/IAP） |
| `36-…/微隔离与软件定义边界-SDP-MicrosegmentationSDP.md` | 11,054 字符 | 吸收（WireGuard/Tailscale/Calico/东西向盲区） |
| `36-零信任架构-ZeroTrust/README.md` | — | 仅确认目录结构 |
| `33-容器安全-ContainerSecurity/skills/Kubernetes RBAC与安全策略-KubernetesRBACSecurityPolicy.md` | 8,147 + 5,420 字符 | 吸收（RBAC 审计、kube-bench、Calico 安装） |
| `34-API安全-APISecurity/skills/API认证与授权安全-APIAuthAuthorizationSecurity.md` | 14,755 字符 | 部分吸收（SAML/OIDC/MFA 相关段落） |
| `34-…/OWASP API安全测试-OWASPAPISecurityTesting.md`、`GraphQL与微服务API安全-….md` | 分段读 | **丢弃**（OWASP/GraphQL 手法归属 API 类卡片，与本卡主题不重叠） |
| `27-操作系统安全-OSSecurity/skills/macOS安全评估与加固-macOSSecurityHardening.md` | 11,008 字符 | 仅少量吸收（设备平面姿态检查点）；其余丢弃 |
| `27-…/国产操作系统安全加固-DomesticOSSecurity.md` | 12,463 字符 | **丢弃**（见 4. 丢弃理由：命令无法核实） |

（注：上游实际文件名与任务文本略有差异，已按 `ls` 结果为准执行。）

## 2. 已吸收（逐条）

**身份面（`references/iam-pam-ops.md`）**
1. Vault：`wget`/`unzip` 安装、`config.hcl`（raft + TLS + awskms auto-unseal）、`operator init -key-shares=5 -key-threshold=3`、`operator unseal`、`raft list-peers` —— 上游原样。
2. Vault 认证方法：userpass / AppRole（`secret_id_ttl`/`secret_id_num_uses`）/ OIDC / LDAP 启用与登录；补 `vault auth list -detailed`、`vault token capabilities`、通配策略扫描循环（补充）。
3. Vault 策略 HCL（`path` + `capabilities`）与 JIT 最小权限示例；动态凭据：database / aws（assumed_role）/ SSH CA / PKI —— 上游命令原样，角色参数补全为可执行形式。
4. Vault 租约：`sys/leases/lookup` 下钻、`lease lookup/renew`、`lease revoke -prefix`、`token revoke -accessor`、`sys/leases/count`（未验证）、audit 设备启用 —— 结构取自上游，命令按官方 CLI 参考核对。
5. PAM：CyberArk Vault/PSM/CPM/AIM/PTA 五模块描述与密码策略基线（长度 20–30、root 30 天/服务账号 90 天、禁重复前 5 次）—— 上游原样；Teleport `tsh`/`tctl` JIT、申请审批、会话回放 —— 已核验的命令。
6. SAML 2.0 八类断言字段的「必须校验 / 缺失后果」表（Signature 只验 Response 的断言替换、Issuer、NameID Format、Conditions、AudienceRestriction、SubjectConfirmationData、AuthnStatement、AttributeStatement 属性注入）+ `xmllint`/`openssl`/`xmlsec1` 命令。
7. OIDC：discovery/JWKS 拉取、不验签读 id_token、六类错误配置（`none`/RS256-HS256 混淆、aud/nonce 缺失、无 PKCE、redirect_uri 通配、jku/x5u/kid 未白名单、JWKS 轮换未校验）。
8. MFA 弱面：TOTP 无速率限制（爆破骨架 + 限速探测循环 + Keycloak `kcadm.sh` 策略读取）、推送轰炸（Entra/Okta 日志命令 + 判定特征）、降级清单（备用通道/应用专用密码/条件访问排除组/设备码流等）+ 条件访问策略枚举命令。
9. 身份生命周期：AD（`Search-ADAccount`、`Get-ADGroupMember`）、AWS（credential report、无 MFA/无密钥用户）、GCP（SA 密钥、owner 绑定）、Azure（role assignment、`az ad app credential list`）、Keycloak（禁用用户、活跃会话）审计命令 + 回收清单。
10. AD 审计：PingCastle（`--healthcheck/--carto/--hc-conso/--scanner aclcheck,localadmin,nullsession,spooler`）、`PurpleKnightCmd.exe`、`SharpHound.exe -c All`、`auditpol /set /subcategory:...`、PowerView `Get-ObjectAcl` 查复制权限 —— 上游原样，仅补 `--privileged` 建议。
11. 云 IAM：aws `list-policies`/`get-policy-version` 通配扫描循环、`list-entities-for-policy`、`get-role` 信任策略、`simulate-principal-policy`、Access Analyzer、`get-account-summary`；gcloud IAM policy/SA keys/`asset search-all-iam-policies`；az role assignment/role definition/sp list。

**网络面（`references/zerotrust-ztna-microseg.md`）**
12. 三平面表（身份/设备/网络）与 NIST SP 800-207 七原则 + PDP/PEP 落地检查点 —— 上游摘要改写。
13. Cloudflare Access：cloudflared 安装/login/create/route dns/config.yml/run、Access 策略 API、WARP 客户端安装注册、Access JWKS 端点 —— 命令原样，绕过点（源站直连、`Include: Everyone`、Service Token、路径规范化、`Cf-Access-*` 头伪造）为补充。
14. Zscaler ZPA / Appgate SDP 配置检查点（App Connector 组、Server Groups 过宽、SAML 属性映射、Entitlements 粒度、设备脚本、客户端强制）—— 上游描述改写为核对清单；两产品均无公开 CLI，未编造命令。
15. WireGuard：`wg genkey/genpsk/pubkey`、`wg0.conf`、`wg-quick up`、`systemctl enable wg-quick@wg0`、`wg show/dump/showconf` —— 上游原样 + 审计点（AllowedIPs 全量与节点互访）。
16. Tailscale：安装脚本、`tailscale up --authkey ... --advertise-routes --accept-routes --ssh`、`status --json`、`whois`、`ping`、`lock status`；ACL 只能控制台/API 改（未验证），审计 `dst: ["*:*"]` —— 上游原样 + 补充。
17. 微隔离：Calico `GlobalNetworkPolicy`（`selector: all()`, `types: [Ingress, Egress]` 默认拒绝）+ 命名空间放行 `NetworkPolicy` YAML 结构、`calicoctl` 导出/查看 Felix 配置、`kubectl create -f tigera-operator.yaml` —— 上游原样；另补纯 K8s `networking.k8s.io/v1` 示例与「选择器标签不存在则静默失效」。
18. K8s 审计：`kubectl auth can-i <verb> <res> --as=system:serviceaccount:...`、rolebindings/clusterrolebindings grep（delete/secrets/`"*"`）—— 上游原样；补 `kubectl auth can-i --list --as=`、`kube-bench run --targets master,node,etcd,policies`、hostNetwork/automount jsonpath。
19. 东西向盲区与 mTLS 失效点：无 NetworkPolicy = allow-all、只 Ingress 无 Egress、hostNetwork/NodePort/169.254.169.254/CoreDNS/kubelet:10250 漏洞面；Istio **PERMISSIVE 下明文流量不做认证/授权校验**（官方行为）、未注入命名空间、sidecar 只覆盖 TCP；`istioctl x authz check/describe`、`kubectl get peerauthentication -A` 核验命令。

## 3. 原样搬自上游（命令级）
Vault 安装/config.hcl/`operator init|unseal|status`、`vault mount database` 旧写法、database/aws/ssh/pki 动态凭据写入、`vault lease renew|revoke -prefix`、CyberArk 五模块与密码策略基线、`Purge/PurpleKnight`… → 具体为 `PurpleKnightCmd.exe`、PingCastle 全套参数、`SharpHound.exe -c All`、`auditpol /set /subcategory`、PowerView `Get-ObjectAcl`、`kubectl auth can-i` 三条、`kubectl get rolebindings/clusterrolebindings -o yaml | grep`、`kubectl create -f tigera-operator.yaml`、Calico 两段 YAML 结构、cloudflared 全序列、WARP 安装、WireGuard 全序列、`sudo tailscale up --authkey tskey-auth-xxxx …`、（上游 CloudIAM 的）`aws accessanalyzer …`、`az rest …/conditionalAccess/policies`、`./kube-bench --config-dir cfg --config cfg/config.yaml`。

## 4. 丢弃（含理由）
1. **AD 域攻击方法论**（Kerberoasting/ADCS/委派/DCSync/横向/接管）—— 本库已有 `windows-ad-pentest`/`active-directory`/`account-takeover-chain`，按要求不重复；只保留审计命令。
2. **上游自编 Python class / 伪代码骨架**（ZT 设计与微隔离章节的类结构、策略校验脚本、CyberArk 抽象类）—— 按要求不作为内容；其语义已改写为检查点清单。
3. **国产操作系统加固命令**（`kylin-security-config`、`uos-security-center`、`kysec-tools`、`dde-security-tools`、`uos-audit-tool` 等）—— 无法在官方文档/本机核实，疑为上游臆造；为守「禁止编造命令」直接不入卡（审计语义上真正可用的 `augenrules --load`/`ausearch`/`pwquality.conf`/`/etc/pam.d` 归入 OS 类卡片，不属本卡主题）。
4. **macOS 加固细节**（FileVault/TCC/socketfilterfw 具体项）—— 与 IAM/PAM/零信任主题仅弱相关，只留设备平面姿态一句，其余归 `macos-reverse`/OS 卡。
5. **OWASP API Top 10 与 GraphQL 手法**—— 归属 API 类卡片；本卡只吸收其认证/授权/MFA 段落。
6. **上游未核实的厂商 REST/PACLI 语法**（CyberArk PACLI、Zscaler 内部 API）—— 不编造，改为「检查点 + 现场 help」表述。
7. 上游的「合规/成熟度评分」类内容（等保条目、成熟度等级）—— 对进攻视角无操作价值。

## 5. 补充（上游没有、由本卡新增）
- Vault：`vault token capabilities` 权限自证、策略通配扫描循环、`sys/leases/count`（未验证）、「审计设备为空 = JIT 无日志」这一结论性检查、`sys/mounts`、`kv metadata`。
- Teleport：`tsh request review --approve`、`tsh play`、`tctl tokens add --type=node`、审计点（`node_labels=*`、`max_session_ttl`、`session_recording=off`、自审）。
- SAML/OIDC：八字段校验表、OIDC 六项错误配置 → 可打点映射、id_token 不验签解码命令。
- MFA：TOTP 爆破骨架与限速探测、推送轰炸判定特征、条件访问排除组/namedLocations/authenticationMethodsPolicy 枚举（后两者标未验证）、设备码流与 OAuth 同意钓鱼旁路。
- 生命周期：`Search-UnifiedAuditLog`（Purview）、`az rest auditLogs/directoryAudits`、Keycloak 活跃会话、以及「IdP 停权 ≠ 应用停权」的回收清单。
- 云 IAM：`aws accessanalyzer create-analyzer`、`gcloud asset search-all-iam-policies`、`az ad app credential list`、`iam:PassRole`/`serviceAccountTokenCreator` 提权面。
- 零信任面：Cloudflare Access JWKS 与 Service Token/path 规范化绕过、Tailscale ACL `*:*` 审计、纯 K8s NetworkPolicy YAML、`kubectl auth can-i --list`、hostNetwork/automountServiceAccountToken jsonpath、`istioctl x authz check/describe`、PERMISSIVE 语义结论。

## 6. 更正与未验证清单
- **更正**：上游 `aws accessanalyzer list-findings --analyzer-name` → 实际参数为 `--analyzer-arn`（已在卡内标注更正）；上游 `aws verifiedaccess create-trust-provider` 命名空间与 AWS CLI 不符（Verified Access 属 EC2 API），**未采用**该写法。
- **标注未验证（卡内显式）**：`xmlsec1 --id-attr:ID` 写法、`vault read sys/leases/count`、Microsoft Graph `policies/authenticationMethodsPolicy` 与 `identity/conditionalAccess/namedLocations`、Okta `/api/v1/logs?filter=` 表达式、CyberArk PACLI 语法、Tailscale CLI 修改 ACL、Istio ambient 下 hostNetwork pod 覆盖范围。
- 所有被核验过的命令依据：Vault CLI/lease 文档、PingCastle 参数表、Teleport `tsh/tctl` 文档、AWS CLI `accessanalyzer`、Istio `istioctl` 与 PeerAuthentication 文档（会话内已检索确认）。

## 7. 交付自检
- 行数：`iam-pam-ops.md` 220/220 ✓、`zerotrust-ztna-microseg.md` 160/160 ✓、`DRAFT-SKILL.md` 正文 64 行 ≤120 ✓（frontmatter 仅 `name`/`description`，description 首 57 字符内含「审计企业 IAM/PAM/零信任」触发短语）。
- 铁律核对：无自造命令（不确定项均标注）；无 AD 域攻击方法论重复；命令均可直接照敲。
- 内容侧限制：Zscaler ZPA / Appgate SDP / CyberArk 仅给出控制台配置检查点，未提供未经核实的 CLI。
