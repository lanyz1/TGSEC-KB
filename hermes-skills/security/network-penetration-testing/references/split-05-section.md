## 四、内网信息收集

### 4.1 内网探测（经代理）

```bash
# 存活主机发现（分段，先高频端口后全量）
proxychains nmap -sn 10.0.0.0/24
proxychains nmap -sT -Pn -p 22,80,443,445,88,389,636,1433,3306,3389,6379,5985 10.0.0.0/24
# RustScan 快速全端口 + 定向 nmap 服务识别
rustscan -a 10.0.0.0/24 -b 2000 -- -sV

# 服务识别
proxychains nmap -sT -Pn -sV -p 88,389,445,636 10.0.0.1
# 域控识别特征：88(Kerberos)+389(LDAP)+636(LDAPS)+3268(GC) 同时开放
# 发现域控后先做"域内账号可控性"测试，而非直接爆破
```

### 4.2 内网关键服务攻击面

| 端口 | 服务 | 攻击方向 |
|------|------|---------|
| 88 | Kerberos | 票据攻击/ASREPRoast/Kerberoast |
| 389/636 | LDAP/LDAPS | 域信息枚举/LDAP 注入 |
| 445 | SMB | SMB Relay/共享枚举/永恒之蓝类 |
| 135 | RPC | DCOM/端口映射/认证胁迫 |
| 5985/5986 | WinRM | PowerShell Remoting |
| 3389 | RDP | 弱口令/RDP 劫持 |
| 1433 | MSSQL | xp_cmdshell/链接服务器/代理凭据 |
| 3306 | MySQL | 弱口令/提权 UDF |
| 6379 | Redis | 未授权/主从复制 RCE |
| 27017 | MongoDB | 未授权访问 |
| 8443 | K8s API | 未授权/K8s 渗透 |
| 8006 | Proxmox/虚拟化 | 管理面接管 |
| 21/22/873 | FTP/SSH/rsync | 弱口令/匿名/镜像泄露 |

### 4.3 BloodHound 图分析与攻击路径（CE v8）

**部署与采集：**
```bash
# BloodHound CE v8（SpecterOps，2025 年后 Legacy 弃用，Kali 2025.3+ 自带）
docker compose up -d                              # 官方 docker-compose 方式
# 域内 Windows 主机上运行采集器
SharpHound.exe -c All,GPOLocalGroup --outputdirectory C:\temp\
# Linux 端采集（可选）
bloodhound-python -u user -p pass -d corp.local -ns 10.0.0.1 --zip

# 导入 zip/json 后内置查询
# - Shortest Paths to Domain Admins from Owned Principals
# - Find Principals with DCSync Rights
# - Find Computers where Domain Users are Local Admin
# - Find All Paths from Kerberoastable Users
```

**核心 Cypher 查询（红队常用）：**
```cypher
// 从已拥有用户到域管的最短路径
MATCH p=shortestPath((n)-[r*1..]->(m:Group))
WHERE n.name =~ 'USER.*' AND m.name =~ 'DOMAIN ADMINS.*' RETURN p
// 拥有 DCSync 权限的主体
MATCH p=(m)-[:GenericAll|WriteDacl|WriteOwner*1..]->(dc:Domain)
WHERE dc.objectid =~ 'S-1-5-21.*' AND NOT m.objectid =~ 'S-1-5-21.*-512' RETURN p
// 可达非约束委派主机
MATCH p=(n)-[r:AdminTo|GenericAll*1..]->(c:Computer)
WHERE c.unconstraineddelegation = true RETURN p
// 高价值 ACL 滥用点（GenericWrite/GenericAll 于特权组）
MATCH p=(n)-[:GenericWrite|GenericAll|WriteDacl|WriteOwner]->(g:Group)
WHERE g.name =~ 'DOMAIN ADMINS.*|ENTERPRISE.*' RETURN p
```

**图分析实战心法：**
```
- 标记 owned 节点后重新计算路径 → 每次新凭据都刷新分析
- 路径优先级：ADCS > 委派 > ACL > 常规成员关系（ADCS 路径往往一步到域管）
- 优先验证"低成本高收益"路径：可离线破解（Kerberoast）> 需要触发认证（Coercion+Relay）> 需要写 ACL
- BloodHound CE v8 OpenGraph：可扩展到 GitHub/Jamf/Okta/Snowflake，混合身份路径需重点关注（见 6.6）
```

