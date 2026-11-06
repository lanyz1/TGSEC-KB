## 十一、XPath注入在SAML/SSO中的滥用

### 11.1 SAML中的XPath使用
SP（服务提供方）解析SAML Response时用XPath提取身份字段：
```
//saml:Assertion/saml:Subject/saml:NameID
//saml:Assertion/saml:AttributeStatement/saml:Attribute
//saml:Response/saml:Assertion[1]
```
若解析逻辑使用**文档级XPath**（`//...`按文档顺序取第一个匹配）而非**签名覆盖子树内查询**，即产生认证绕过。

### 11.2 文档级XPath缺陷（CVE-2026-18092实战）
Perl Net::SAML2 <0.86：`new_from_xml`用`//saml:Assertion/...`取NameID/Attribute（文档顺序第一个），而XML::Sig只验证签名Reference URI指向的子树。攻击者持有任一IdP签名断言，即可在其**文档序之前**插入自建未签名断言 → 签名仍验证通过 → SP采用攻击者的NameID/属性 → 任意用户冒充。CVSS 8.1。
```
# 测试方法
1. 捕获一个合法签名的SAML Response
2. 在文档中插入第二个未签名Assertion（置于签名元素之前）
3. 观察SP是否采用插入断言中的身份/角色
```

### 11.3 XSW签名包装攻击（XML Signature Wrapping）
签名验证与业务处理用不同解析器/不同视图时，通过**包装**保留签名、替换消费数据：
- 双根/多根包装：在`<Response>`外再包一层，或复制`<Assertion>`副本
- 元素替换：签名的`<Reference URI="#id">`指向的元素替换为攻击者元素（ID属性重用）
- Void Canonicalization / 属性污染：利用规范化和命名空间解析差异（Black Hat EU 2025 "The Fragile Lock"）
- 属性轮子：借合法签名的id，将`<Attribute>`内容替换后重放

### 11.4 2025-2026 SAML/XML XPath相关漏洞速查
| CVE | 组件 | 危害 | 要点 |
|-----|------|------|------|
| CVE-2026-18092 | Perl Net::SAML2 <0.86 | 认证绕过（CVSS 8.1） | 文档级XPath读身份 |
| CVE-2025-25291/25292 | ruby-saml | 认证绕过 | Nokogiri解析器差异（XSW） |
| CVE-2026-49289 | simplesamlphp/saml2 <4.20.3 | DoS（CVSS 8.7） | XPath Transform过程注入 |
| CVE-2026-46490 | samlify <2.13.0 | 提权（CVSS 8.8） | AttributeValue未转义注入 |
| CVE-2026-55789 | Logto <1.41.0 | 提权 | SAML模板字符串替换注入 |
| CVE-2026-40165 | authentik | 认证绕过 | NameID XML注释注入 |

### 11.5 SAML测试方法
```
1. SAMLResponse参数Base64解码→修改→重编码发送（XML注释/属性/断言注入）
2. 注入点候选：NameID、AttributeValue、AudienceRestriction、SessionIndex
3. XPath注入探测：NameID中注入 ' or '1'='1 观察身份变化
4. XSW：插入副本断言/双根/ID重用，观察是否接受
5. 属性提权：role/group/admin字段注入新值（如 samlify CVE-2026-46490）
```
**注意**：SAML断言多被压缩（`<samlp:Response>` + deflate），先解压再修改；测试请使用专属测试IdP。

