## 一、XXE 完整攻击面与解析器默认配置风险矩阵

### 1.1 XML 输入点（攻击面测绘）
| 输入点 | 格式 | 实战优先级 |
|--------|------|-----------|
| 请求体 `Content-Type: application/xml` | 标准 XML POST | ★★★★★ |
| SOAP 接口 | SOAP Action + XML | ★★★★★ |
| SAML 单点登录 | SAML Request/Response | ★★★★★（认证绕过）|
| SVG 文件上传 | SVG 含 XML | ★★★★★ |
| DOCX/XLSX/PPTX | OOXML 压缩包内 XML | ★★★★★ |
| PDF（XFA/FDF/XFDF） | 表单 XML 流 | ★★★★☆（Tika/Foxit 新CVE）|
| EPUB 电子书 | OPF/XHTML | ★★★☆☆ |
| ZUGFeRD 电子发票 | 发票 XML 内嵌 PDF | ★★★★☆（Kivitendo CVE-2025-66370）|
| RSS/Atom 订阅导入 | XML 格式 | ★★★☆☆ |
| XML-RPC 接口 | WordPress/MovableType | ★★★☆☆ |
| REST API（接受 XML） | 尝试 JSON 换 XML | ★★★★★（最常被忽略）|
| Web Service | WSDL/SOAP | ★★★☆☆ |
| XML 配置导入导出 | Spring/Struts 配置文件 | ★★★☆☆ |
| Java XMLDecoder/序列化 XML | XML 反序列化 | ★★★★☆（可 RCE）|
| XSLT 处理 | XSL 样式表 | ★★★★☆（Xalan 可 RCE）|
| XMPP/Jabber 消息 | XML 协议 | ★★☆☆☆ |
| **LLM/AI 应用文档上传** | RAG 文档解析（PDF/DOCX/SVG/HTML→XML） | ★★★★★（2025 新战场）|
| 移动端/桌面应用导入 | 各种 XML 格式 | ★★☆☆☆ |

### 1.2 解析器默认配置风险矩阵
| 解析器/库 | 默认外部实体 | XXE 风险 | 备注（v3.0 深化）|
|----------|------------|---------|------------------|
| Java DOM/SAX/StAX（Xerces） | 默认启用 | **高** | 未设置 FEATURE_SECURE_PROCESSING 即可利用 |
| Java SAXParserFactory/XMLReader/DocumentBuilderFactory | 默认启用 | **高** | 老代码高发，详见第四章 4.5 |
| JAXB/Unmarshaller | 默认启用 | **高** | 需配合安全 XMLReader |
| .NET XmlDocument（<4.5.2） | 默认解析 DTD | 高 | 现代 .NET 需显式 `XmlReaderSettings.DtdProcessing=Parse` 才中招 |
| .NET XmlTextReader（老） | ProhibitDtd=false | 中 | 遗留代码 |
| PHP SimpleXML/DOM（libxml2） | PHP <8.0 默认开启 | 高 | PHP 8.0+ 默认 `LIBXML_NONET` 禁外部实体，但 `LIBXML_DTDLOAD` 手动开启仍可绕 |
| Python lxml（libxml2） | 默认 `resolve_entities=True` | **高** | **lxml 5.x 有 meow:// 加固绕过技巧（见 5.4）** |
| Python xml.sax / minidom | 默认启用 | 高 | defusedxml 是唯一官方安全替代 |
| Python xml.etree.ElementTree | 默认不处理外部实体 | 低 | 但拒绝服务（Billion Laughs）仍可 |
| Ruby REXML | 有 entity_expansion_limit | 中 | 外部实体需注意版本差异 |
| Ruby Nokogiri | 默认不加载外部实体 | 低 | **JRuby 实现 NONET 失效 SSRF（CVE-2026-57234，修复 1.19.4）** |
| Node.js fast-xml-parser | `processEntities` 默认开 | 中→高 | **CVE-2026-25896 实体 shadow、CVE-2026-33036 数字字符引用 DoS** |
| Go encoding/xml | 默认无 DTD 外部实体支持 | 低 | 但内部实体扩展 DoS 仍存在 |
| SAP/NetWeaver | 默认启用 | **高** | 历史多个 CVE |
| Oracle XML DB | 默认启用 | 高 | 企业遗留系统 |
| Apache Tika | 未硬化 | **高** | **CVE-2025-66516 PDF XFA XXE（CVSS 10）** |
| libxml2（C/C++ 通用） | 2.9+ 默认不解析外部实体 | 低→中 | **2.9.11-2.11.0 有 UAF DoS（CVE-2026-6653）；5.4.0 加固后仍有绕过研究** |

### 1.3 XXE 危害类型
```
1. 任意文件读取（file:// + 本地文件，含源码/密钥/配置）
2. SSRF（http/https/ftp/gopher 等任意协议 + 内网探测）
3. 内网端口扫描与内网服务攻击（Redis/ES/Docker API 等）
4. DoS（Billion Laughs / Quadratic Blowup / 外部资源 DoS）
5. RCE（PHP expect://、Java XSLT/XMLDecoder、phar:// 反序列化等）
6. 云元数据窃取（AWS/GCP/Azure/阿里云 IAM 临时凭证）
7. 认证绕过（SAML XXE 读 SP 私钥/断言伪造）
8. Windows NetNTLMv2 哈希捕获（UNC 路径 + responder）
9. 信息泄露（配置/数据库口令/CI 密钥/备份文件）
```

