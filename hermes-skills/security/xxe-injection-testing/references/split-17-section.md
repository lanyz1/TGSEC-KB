## 十五、修复建议

### 15.1 解析器配置基线（首选，五要素全关）
```java
// Java DOM/SAX
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
dbf.setXIncludeAware(false);
dbf.setExpandEntityReferences(false);
// StAX
xif.setProperty(XMLInputFactory.SUPPORT_DTD, false);
xif.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
```
```csharp
// .NET
XmlReaderSettings settings = new XmlReaderSettings {
    DtdProcessing = DtdProcessing.Prohibit,   // 或 Ignore
    XmlResolver = null                         // 关键！
};
```
```python
# Python：直接使用 defusedxml（官方唯一推荐）
from defusedxml import minidom, sax, ElementTree, lxml
# lxml 手动关闭
etree.XMLParser(resolve_entities=False, no_network=True)
```
```php
// PHP 8.0+ 已默认禁外部实体；老代码务必
libxml_disable_entity_loader(true);   // PHP <8.0
// 或加载时 LIBXML_NONET | LIBXML_NOENT 不要同时使用
```
```js
// Node.js：fast-xml-parser 升级 ≥5.5.6（修 CVE-2026-25896/33036），
// 或 processEntities:false + 关闭 DOCTYPE 处理
```

### 15.2 输入与架构层
- **能不用 XML 就不用**：接口优先 JSON，协议优先 REST
- **白名单校验**：XML 长度/嵌套深度/DOCTYPE 存在性前置校验（注意：校验层自己别被 DoS）
- **最小权限**：XML 解析进程以低权限账户运行，限制文件系统/网络访问
- **网络隔离**：解析服务禁止访问元数据网段与内网（出站白名单 + egress 过滤）
- **沙箱**：文档解析类功能（Tika/Poppler/预览）跑在容器/沙箱，仅挂载必要文件
- **依赖治理**：升级 Tika ≥3.2.2、CXF ≥4.2.3、Netty ≥4.1.136、fast-xml-parser ≥5.5.6、langchain-text-splitters ≥0.3.9、Nokogiri ≥1.19.4（对照第十一章 CVE 表）

### 15.3 WAF 与检测
- 拦截规则：`<!DOCTYPE`、`<!ENTITY`、`SYSTEM`、`PUBLIC`、`file:`、`http:`、`expect:`、`jar:`（注意编码变体，配合解码层）
- 检测 OAST 回调（Collaborator/Interactsh 域名比对）
- 日志告警：XML 解析异常 + 外部请求同时出现

### 15.4 SDL 固化
- 安全编码规范内置安全 XML 解析模板（Java/C#/Python/PHP/JS 各一）
- CI 中跑 Semgrep/CodeQL XXE 规则，新代码禁入
- 文档解析类新功能上线前强制走安全评审

