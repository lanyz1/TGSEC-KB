## 十四、测试检查清单

### 14.1 攻击面测绘
- [ ] 枚举所有接收 XML 的接口（application/xml、text/xml、SOAP、XML-RPC）
- [ ] 尝试将 JSON 请求改写为 XML（Content-Type 切换）观察解析行为
- [ ] 梳理文件上传功能（SVG/DOCX/XLSX/PPTX/PDF/EPUB/FDF/ZUGFeRD/XML）
- [ ] 梳理 SAML/SSO 流程、RSS/Atom 订阅导入、webhook 回调
- [ ] 记录解析器类型与版本（响应头/报错/指纹）

### 14.2 漏洞确认
- [ ] 内部实体探针（&test; 回显 XXE_OK）
- [ ] 外部实体回连探测（DNS/HTTP 外带）
- [ ] 参数实体回连探测
- [ ] 有回显：file:///etc/passwd 与 win.ini 文件读取
- [ ] 盲注：外部 DTD OOB 外带 / 错误消息盲提取
- [ ] XInclude 注入（无 DOCTYPE 时）
- [ ] Content-Type 混淆尝试

### 14.3 深度利用
- [ ] 全协议遍历（file/http/ftp/gopher/dict/php://filter/jar/netdoc/expect/data/ldap/tftp）
- [ ] CDATA 包装提取特殊字符文件
- [ ] 编码绕过（UTF-7/UTF-16/实体编码/php filter）
- [ ] SSRF：本机端口扫描、内网段扫描、云元数据（AWS/GCP/Azure/阿里云/腾讯云）
- [ ] 内网服务攻击（Redis/Docker API/ES/管理 API）
- [ ] SAML 认证绕过尝试
- [ ] RCE 尝试（PHP expect/phar、Java XSLT/XMLDecoder、jar 写文件链）
- [ ] Windows NetNTLMv2 捕获
- [ ] DoS 验证（Billion Laughs/Quadratic Blowup，**仅授权低危环境**）

### 14.4 WAF/防护绕过
- [ ] 关键字过滤绕过（大小写/注释/空白/实体拼接/字符引用）
- [ ] 外部实体开关差异利用（general/parameter 独立开关）
- [ ] 本地 DTD 技巧（dtd-finder）无出网盲提取
- [ ] 二次解析面（JSON 内嵌 XML、模板渲染、配置反序列化）

### 14.5 后渗透
- [ ] 读配置/密钥/源码 → 凭据收集
- [ ] 内网横向（借 XXE 为 SSRF 跳板）
- [ ] 清理测试痕迹（临时文件、恶意文档）

