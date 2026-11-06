## 十三、修复建议

### 13.1 代码层面（根治）
- **杜绝字符串拼接**：使用框架参数化API（Spring `AndFilter/EqualsFilter`、ldapjs过滤器类、`ldapTemplate.authenticate(Dn, filter)`）
- **正确转义**：过滤器值用RFC 4515转义（`\2a \28 \29 \5c \00`），DN组分用RFC 4514转义（`+ ; < > \ # " , =`），两者不可混用
- **属性名/结构位白名单**：属性名、基DN等结构位禁止由用户输入决定，用枚举白名单
- **输入校验**：用户名白名单（字母数字+`@.-_`），长度限制（防超长DoS）
- **错误信息收敛**：不返回LDAP错误详情/过滤器语法信息
- **认证与搜索分离**：优先使用Bind认证而非"搜索+比较"式过滤器认证；Bind的DN由服务器端映射

### 13.2 加固与依赖
- **升级修复库**：python-ldap ≥3.4.5（CVE-2025-61911）、PAC4J ≥4.5.10/5.7.10/6.4.1（CVE-2026-40459）、Yamcs ≥5.12.7（CVE-2026-42568）、OpenAM ≥16.1.1（CVE-2026-46619）、Samba（CVE-2026-58222）、389 DS（CVE-2026-11770）
- **最小权限绑定**：应用绑定账号仅授所需读写权限，禁止管理员绑定；服务账号独立，杜绝共享凭据
- **禁用匿名绑定**：rootDSE以外全部要求认证
- **启用LDAPS并校验证书链**：拒绝自签/无效证书；强制StartTLS（禁止降级）
- **AD加固**：启用LDAP签名（Require signing）+ 通道绑定（`LdapEnforceChannelBinding=2`），参考ADV190023
- **防护NTLM Relay**：启用EPA/CBT、SMB签名、清除LLMNR/NBNS
- **敏感属性ACL**：限制userPassword/unicodePwd/msKds-RootKeyData/description读取

### 13.3 监控检测
- **LDAP审计日志**：监控异常过滤器（含`*`、`|`、`(`的登录过滤器）、批量枚举、异常Compare/Modify
- **WAF规则**：拦截过滤器元字符的登录/搜索参数；对`(&(|`、`objectClass=*`、`userPassword=*`特征告警
- **告警关联**：同一来源大量登录尝试+不同username → 通配符接管/盲注行为
- **AI/Agent平台**：对Agent的LDAP查询做同等级审计与最小化授权（OWASP Agentic Top 10）

