## 检查清单

### 信息收集
- [ ] 确认目标使用反序列化（特征指纹：rO0AB/AC ED 00 05/O:N:/`\x80\x03`/__VIEWSTATE/rememberMe/@type）
- [ ] 枚举全部入口：HTTP body/Cookie/Header/消息队列/RPC（RMI 1099、T3 7001、IIOP 3700、JMX 9010）/文件上传
- [ ] 识别依赖与版本：commons-collections/beanutils/fastjson/jackson/snakeyaml/xstream/log4j 等
- [ ] 确认 JDK 版本（JNDI/BCEL/CC 链可用性矩阵）与中间件类型
- [ ] 测试目标出网能力（DNS/HTTP/RMI/LDAP）决定出网/不出网策略
- [ ] 检测过滤器存在性：JEP 290 ObjectInputFilter、SerialKiller、resolveClass 白名单、框架 ClassFilter

### 无害探测
- [ ] URLDNS / DNSLog 外带确认反序列化入口存在（不触发 RCE）
- [ ] sleep 时间侧信道验证链是否生效
- [ ] 错误信息泄露收集（依赖名/类路径/框架版本）

### 漏洞利用（授权范围内）
- [ ] 按依赖选择链：CC6 盲打 → CB1（Shiro）→ JDK-only（JEP 290 环境）→ 框架链（Spring/Groovy/ROME）
- [ ] 中间件专项：Shiro rememberMe / WebLogic T3-IIOP-XMLDecoder / JBoss JMXInvoker / Jenkins CLI 与 config.xml
- [ ] 原生反序列化过滤器绕过：TC_PROXYCLASSDESC（CVE-2026-47065）/ depth>1 白名单短路（CVE-2026-62263）/ JDK-only 链
- [ ] JSON 类反序列化：Fastjson @type 绕过（详见 fastjson-exploitation 技能）
- [ ] PHP：unserialize 入口 / phar:// 触发 / Session 引擎不一致 / 框架 POP 链
- [ ] Python：pickle 入口 / PyYAML unsafe_load / torch.load / find_class 绕过
- [ ] AI 框架：LangChain dumps/loads（lc 键）、LangGraph checkpoint、vLLM ZeroMQ、向量库索引、MCP 配置
- [ ] 不出网场景：BCEL / TemplatesImpl / c3p0 二次反序列化 / 文件写入链 / 内存马
- [ ] 回显与验证：DNS/HTTP 外带、异常回显、写 WebShell、延时盲打

### WAF 对抗
- [ ] chunked 分块传输 / Content-Type 变换 / Gzip 压缩
- [ ] 序列化数据混淆（TC_RESET/垃圾字节/深度嵌套）与编码变形（Base64/Hex/Unicode）
- [ ] HPP 参数污染 / Header 注入 / POST→GET 转换

### 收尾
- [ ] 清理测试痕迹（WebShell/文件/计划任务/内存马进程）
- [ ] 编写修复建议并输出漏洞报告（POC/影响/修复/证据链）

