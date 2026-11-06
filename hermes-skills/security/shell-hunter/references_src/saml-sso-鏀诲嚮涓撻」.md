# SAML SSO 断言攻击专项

> 企业 SRC/授权测试常见面：目标用 SAML SSO 联邦登录时，重点测签名覆盖缺陷、XML 签名包装、断言属性篡改、Audience/Recipient 校验、重放与新鲜度、账户映射信任、XML 解析弱点。

## 一、协议与角色

| 角色 | 作用 | 攻击面 |
|------|------|--------|
| IdP（身份提供方） | 认证用户、签发断言 | issuer 信任、签名密钥、属性声明 |
| SP（服务提供方） | 消费断言、授予会话 | ACS 校验、签名验证、属性映射 |
| 浏览器 | 中继 | SAMLRequest/Response 拦截重放 |

| Binding | XML 传输方式 | 攻击面 |
|---------|-------------|--------|
| HTTP-Redirect | base64+deflate 在 URL query（`SAMLRequest=`/`SAMLResponse=`） | URL 篡改、日志泄露、deflate 缺陷 |
| HTTP-POST | base64 在表单 POST body 到 ACS | body 篡改、签名包装 |
| HTTP-Artifact | artifact 通过后端通道解析 | artifact 重放 |
| SAML SOAP | 直接到属性权威 | SOAP 注入 |

**核心概念**：SAML Response 包一个或多个 Assertion。Response、Assertion 或两者都可能被签名。**签名位置（signed node）错误是最常见缺陷。**

## 二、签名覆盖缺陷（逢 SAML 先测第一类）

| 缺陷 | 现象 | 测试方法 |
|------|------|---------|
| 未签名的 Response | Response 未签名，只签了 Assertion | 篡改 Response 级属性（Destination/IssueInstant/InResponseTo）后重放 |
| 未签名的 Assertion | Assertion 未签名 | 篡改断言内 NameID/角色/属性 |
| 签名了错误节点 | 签了 IdP 的元素或 ds:Object 内容 | 用原始签名的 Response 包一个篡改的 Assertion（XSW） |
| 签名未验证 | SP 只检查"存在签名"不验证签名值 | 重新签名/任意密钥自签声明，看 SP 是否接受 |
| 断言与响应分离 | SP 信任未签名 assertion 只因传递在签名 response 内 | 剥离 signature 元素重放 |

## 三、XML 签名包装攻击（XSW1–XSW8）

核心：**保持原始签名节点与其引用数据完好，同时注入攻击者控制的第二个节点/元素**，让 SP 验证了"签名存在的那个节点"却消费了"另一个节点"。

常见变体：
1. **XSW1**：在 SignedInfo 后插入第二个 `<ds:Object>`/主体元素，签名仍引用原对象 → 把攻击断言塞进新位置
2. **XSW2**：把带签名节点移动到文档别处，在原引用位置放攻击内容
3. **XSW3**：为攻击内容创建一个新 `<ds:Object>` id，改 Reference URI 指向它（如果校验宽松）
4. **XSW4/XSW5**：Duplicate object 重复 id 混淆解析器
5. **XSW8/XSW9**：通过操纵命名空间前缀（`<ds:Signature>` 前缀被重定义）让解析器认错节点

**实务**：直接改代码层更有效——拿原始合法 Response，把整个 `<saml:Assertion>` 换成攻击者的断言（含攻击者 NameID/角色），**保留原 Response 的 `<ds:Signature>` 原样不动**，多数字典实现只验证"Response 有签名"而不看断言与签名的绑定关系 → 直接成立。

## 四、断言属性篡改

| 字段 | 篡改目标 | 后果 |
|------|---------|------|
| NameID | 换成受害者/管理员 | 以他人身份登录 |
| `role`/`Role`/`groups` | 加 admin/role 属性 | 越权角色 |
| `email`/`upn`/`employeeID` | 换他人标识 | 账户映射接管 |
| `NameID Format` | `unspecified`↔`emailAddress` 混用 | 绕过映射格式校验 |
| 自定义属性（`department`/`ssn`/`membership`） | 改成目标值 | 业务越权 |

## 五、Audience/Recipient/Destination 校验缺陷

| 检查 | 缺失后果 |
|------|---------|
| Audience（断言给谁） | 在 A 站抓的 SAML 断言可以投给同 IdP 的 B 站 |
| Recipient（收件人） | 从站点 A 的 POST 抓 Response 直接 POST 到 B 站 ACS |
| Destination（目的地） | 跨站点重放 |
| 名校验（SP 由 IdP 签发的 Assertion 里 issuer） | 攻击者自己的 IdP 签发断言 → 目标 SP 直接接受（IdP 混淆） |

## 六、重放与新鲜度

| 缺陷 | 测试 |
|------|------|
| 无 InResponseTo 校验 | 抓合法 Response 原样重放两次，第二次仍成功 = 重放洞 |
| 无 IssueInstant/NotOnOrAfter 校验 | 改时间戳为过去/未来，仍接受 |
| Session notBefore 失效后断言仍可用 | 登录成功 → 改系统时间再提交 |

## 七、账户映射信任缺陷

| 模式 | 缺陷 | 验证 |
|------|------|------|
| email-only 映射 | SP 按 `email` 找用户，不验证 email 验证过 | 断言里 email 换成受害者邮箱，登录进受害者账户 |
| 大小写折叠 | `<EMAIL-REDACTED>` vs `<EMAIL-REDACTED>` 映射为两个账号 | 大小写变体注册后提权 |
| NameID format 混淆 | 同一实体不同 format 映射到不同账号 | 换 format 重放 |
| 未验证 email 域 | 任意域名 email 都建账户 | `<EMAIL-REDACTED>` 直接进 |

## 八、XML 解析弱点联动

- **XXE**：SAML 是 XML → 测 `xxe-test.md`（OOB 外带、SSRF 云元数据）
- **XInclude**：`<xi:include>` 读取文件
- **Billion Laughs**：实体扩展 DoS
- **注释内签名绕过**：在签名有效内容中注入 `<!--` 注释，解析器忽略注释内容 → 用注释掩盖恶意元素

## 九、实战流程（逢 SAML 快速过）

```
1. 抓一个合法 SAMLResponse（登录流程中拦截）
2. 解码 base64 → 检查签名位置与覆盖范围（Response 级？Assertion 级？都验？）
3. 剥离/保留签名分别重放 → 看是否校验
4. 篡改 NameID/email/role → 重放（未签名面直接成；签名面走 XSW 包装）
5. 跨站点重放（改 Destination/Recipient）
6. 换自己 IdP 签发的断言（idp 混淆）
7. 原样重放测重放漏洞
8. 时间戳野改测新鲜度
9. XML 解析层：XXE/XInclude/实体炸弹
```

**差分即证据**：进受害者账户（header 变成受害者）或角色提升（能看到管理员功能）才算洞。

## 十、修复建议（写报告用）
- 严格验证签名节点：必须验证 `<ds:Signature>` 覆盖整个 `<saml:Assertion>`（含 NameID 与全部属性），用规范化的 XML 验签
- 校验 Audience/Recipient/Destination/Issuer 全部字段
- 强制 InResponseTo 单次使用 + IssueInstant/NotOnOrAfter 时效校验
- 账户映射键用已验证的持久 ID（如 NameID+format 组合），禁止裸 email
- 关闭外部实体解析（XXE），XML 解析器安全配置