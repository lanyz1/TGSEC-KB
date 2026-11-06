## 十五、检测与验证

### 15.1 黑盒检测
```
1. URLDNS（Java）/ DNS 外带（全语言）：无 RCE 副作用，最安全
2. 时间侧信道：payload 内 sleep 10 / Thread.sleep(5000) → 观察响应延迟
3. 错误信息泄露：畸形 payload 触发异常 → 泄露依赖/类路径/反序列化框架名
4. 特征指纹：
   - Java: rO0AB / AC ED 00 05；Cookie rememberMe= → Shiro
   - PHP: O:N:"Class":... 格式；phar:// 探测
   - Python: \x80\x04\x95...；YAML !!python/object 标签
   - .NET: __VIEWSTATE 参数；BinaryFormatter 头 00 01 00 00 00 FF FF
   - Node: _$$ND_FUNC$$_
5. 请求头探测：T3 握手（WebLogic）、/invoker/JMXInvokerServlet（JBoss）、RMI 端口
```

### 15.2 白盒检测与审计清单
```
- [ ] 搜索全部反序列化入口关键字（见 2.2）
- [ ] 判定输入可信度：用户可控？经过签名/MAC/加密验证？来源信任边界？
- [ ] 依赖版本比对已知 CVE（commons-collections/fastjson/jackson/snakeyaml/xstream/log4j 等）
- [ ] 检查过滤器/白名单配置：JEP 290 / SerialKiller / resolveClass 重写是否存在且完整
- [ ] 检查间接反序列化：JSON/YAML/XML 解析器的类型标记开关（enableDefaultTyping/AutoType/TypeNameHandling/FullLoader）
- [ ] AI 应用专项：langchain dumps/loads、checkpoint 存储、torch.load、向量库索引、MCP 配置
- [ ] 数据流验证：可疑入口用 CodeQL/Semgrep 做 source→sink 可达性分析
```

