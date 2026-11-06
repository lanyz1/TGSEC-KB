## 概述

LDAP（轻量级目录访问协议）注入与SQL注入同源（CWE-90：对LDAP查询中特殊元素中和不当），攻击者通过注入LDAP过滤器元字符（`*`、`(`、`)`、`\`、`&`、`|`、`!`）改写查询逻辑，实现**认证绕过、信息泄露、数据盲注提取、权限提升**。由于LDAP目录几乎都是企业的身份基座（Active Directory/OpenLDAP/FreeIPA），一次成功的LDAP注入通常意味着企业身份仓库失守，可沿"注入→信息泄露→域枚举→凭据获取→横向移动→域管"链路直接打通域渗透。

本技能v3.0.0在v2.0基础上深化到**攻防专家实战维度**：不仅覆盖经典AND/OR注入与认证绕过，更深入**RFC 4515过滤器语义与类型混淆、通配符滥用（Wildcard Abuse）横向接管、OID位掩码/位运算盲注提取、OAST外带、非标准属性利用、LDAPS/StartTLS/通道绑定攻击面、主流框架注入差异（Spring Data LDAP/ldap3/ldapjs）、LDAP注入与AD域渗透攻击链联动**，并引入**2025-2026年最新实战漏洞案例**（CVE-2026-46619 OpenAM MSISDN、CVE-2026-40459 PAC4J、CVE-2026-58222 Samba AD、CVE-2026-42568 Yamcs、CVE-2026-11770 389 DS、CVE-2025-61911 python-ldap）与**AI大模型结合**（AI辅助Payload变异、LLM审计拼接代码、Agent/SSO平台LDAP面）。

### 核心概念
- **LDAP过滤器（Filter）**：RFC 4515定义的布尔表达式字符串，用波兰前缀记法，是注入的目标语法
- **DN（Distinguished Name）/RDN（Relative DN）**：条目在目录树中的唯一路径，DN拼接注入与过滤器注入是两类独立攻击面
- **元字符**：`* ( ) \ NUL` 为过滤器转义核心（RFC 4515），`+ ; < > \ # " , =` 为DN转义核心（RFC 4514），两者转义规则不同，混用即漏洞
- **绑定（Bind）**：LDAP认证机制，与"搜索过滤器认证"是两种不同模式——过滤器认证才是注入重灾区
- **OID扩展匹配**：`attr:oid:=value` 语法，AD位掩码（`:1.2.840.113556.1.4.803:`）、递归组成员（`:1.2.840.113556.1.4.1941:`）都是注入可操纵的语义
- **LDAPS/StartTLS**：636端口的SSL/TLS封装与389端口的StartTLS升级，决定中间人/中继攻击面
- **通道绑定/签名**：AD的LDAP安全加固（ADV190023），缺失时NTLM Relay to LDAP可通杀
- **userPassword**：OCTET STRING类型，可用`octetStringOrderingMatch`（OID 2.5.13.18）按字节位运算盲注，这是v3.0新增的高效提取面

### 攻击链全景（v3.0核心方法论）
```
注入点发现 → 过滤器结构推断 → 认证绕过/信息枚举
    ↓
盲注数据提取（布尔/二分/位运算/OAST）
    ↓
AD环境联动：域枚举 → SPN/Kerberoasting → noPac(CVE-2021-42278/42287) → DCSync → 域管
    ↓
AI维度：LLM审计定位拼接点 / AI生成Payload变体加速循环
```

