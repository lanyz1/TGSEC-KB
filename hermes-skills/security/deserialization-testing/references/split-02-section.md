## 一、反序列化攻击面全景

### 1.1 入口识别与指纹特征
| 语言 | 入口点 | 特征指纹 |
|------|--------|---------|
| Java | `ObjectInputStream.readObject()/readUnshared()`、XMLDecoder、XStream、Hessian/Kryo/FST、Jackson `enableDefaultTyping`、Fastjson `@type`、RMI(1099)/JMX(9010)/JNDI/T3(7001)/IIOP(3700)、JMXInvokerServlet | 二进制 `AC ED 00 05`；Base64 以 `rO0AB` 开头；Cookie `rememberMe=`；T3 头 `t3 12.2.1` |
| PHP | `unserialize()`、`phar://` 文件操作、Session 反序列化、`yaml_parse`、`json_decode`+`__wakeup` | `a:2:{i:0;...}` / `O:4:"User":2:{...}` 格式 |
| Python | `pickle.loads()`/`Unpickler`、`yaml.load()`/`unsafe_load()`、`ruamel.yaml`、`torch.load()`、`shelve`、`marshal.loads`、`jsonpickle.decode()`、Celery/Django session | pickle 以 `\x80\x03`/`\x80\x04`/`\x80\x05` 开头；YAML `!!python/object` 标签 |
| .NET | `BinaryFormatter.Deserialize()`、`LosFormatter`、`SoapFormatter`、`NetDataContractSerializer`、`Json.NET TypeNameHandling`、ViewState | BinaryFormatter 头 `00 01 00 00 00 FF FF`；ViewState 为 Base64（可含 `FF 01` 魔术字节） |
| Ruby | `Marshal.load()`、`YAML.load()`（Psych）、`JSON.parse(create_additions: true)` | Marshal 二进制 `\x04\x08` 开头 |
| Node.js | `node-serialize`、`serialize-to-js`、`js-yaml` unsafelyLoad、`safe-obj` 等 | 函数体序列化为 `_$$ND_FUNC$$_function(){...}()` 特征 |

### 1.2 数据传输格式分类
- **二进制原生**：Java 序列化（`rO0AB`）、.NET BinaryFormatter、Ruby Marshal、Python pickle
- **JSON**：Fastjson `@type`、Jackson `@class`/`defaultTyping`、Json.NET `$type`、jsonpickle `py/object`、node-serialize `_$$ND_FUNC$$_`
- **XML**：XStream、XMLDecoder、.NET SoapFormatter、Log4j JNDI（表达式注入）
- **YAML**：PyYAML（`!!python/object/apply`）、SnakeYAML（`!!javax.script.ScriptEngineManager`）、Ruby Psych
- **RPC/分布式**：Hessian/Burlap（Dubbo）、AMF（BlazeDS）、RMI/JRMP、T3/IIOP（WebLogic）、ZeroMQ `recv_pyobj`（vLLM）、gob（Go）
- **特殊触发面**：Phar 元数据（任意文件操作函数触发）、日志（Log4Shell `\${jndi:}`）、模板引擎（freemarker/velocity 的 `objectWrapper`）

### 1.3 常见框架/组件高危 CVE 全景（含 2025-2026 新增）
| 组件 | CVE / 编号 | Gadget / 危害 |
|------|-----------|---------------|
| Apache Commons Collections | CVE-2015-7501 | CC1-CC7 链 |
| Fastjson 1.x / 2.x | 多个 AutoType 绕过 / CVE-2026-16723 / QVD-2026-45876 | JNDI/Gadget-free RCE（详见 fastjson-exploitation 技能） |
| Jackson | CVE-2017-17485 / CVE-2019-12384 | enableDefaultTyping RCE |
| Apache Shiro ≤1.2.4 | CVE-2016-4437 | rememberMe 硬编码密钥 AES-CBC 反序列化 |
| WebLogic | CVE-2015-4852 / CVE-2017-10271 / CVE-2019-2725 / CVE-2020-2555 / CVE-2023-21839 | T3/IIOP/XMLDecoder RCE |
| JBoss/WildFly | CVE-2017-12149 / CVE-2017-7504 | 反序列化 RCE |
| Jenkins | CVE-2015-8103 / CVE-2016-0788 / **CVE-2026-53435**（JEP-200 ClassFilter 绕过，config.xml 任意类型反序列化 + Stapler 路由 → 用户冒充/Script Console Groovy RCE/任意文件读） | 反序列化 RCE |
| Apache Log4j2 | CVE-2021-44228 (Log4Shell) | JNDI 注入 RCE |
| XStream | CVE-2021-21342 等多个 | XML 反序列化 RCE |
| SnakeYAML | CVE-2022-1471 | `!!` 标签 RCE |
| **LangChain / LangGraph** | **CVE-2025-68664（CVSS 9.3，`lc` 键序列化注入→环境变量窃取/类实例化）；CVE-2025-64439（checkpoint 反序列化 RCE）；CVE-2025-67644（SQLite checkpoint SQLi）** | 提示注入→序列化注入→RCE/密钥窃取 |
| **vLLM** | **CVE-2025-32444（CVSS 10.0，mooncake 集成 ZeroMQ+pickle 未认证 RCE）；CVE-2025-24357（torch.load 恶意模型 RCE）** | pickle 反序列化 RCE |
| **PyTorch** | **CVE-2025-32434（torch.load weights_only=True 绕过）** | pickle RCE |
| **python-socketio** | **CVE-2025-61765（Redis 消息队列 pickle RCE）** | 中间件 pickle 投毒 |
| **MCP（Model Context Protocol）** | **STDIO 设计级 RCE（"The Mother of All AI Supply Chains"，12+ CVE，150M+ 下载受影响）；CVE-2026-33032（nginx-ui MCP 未认证命令执行，CVSS 9.8）** | 配置→命令执行；提示注入→工具投毒→数据外带 |
| **Java 过滤器绕过** | **CVE-2026-47065（resolveProxyClass 绕过 ObjectInputFilter，CVSS 9.8）；CVE-2026-62263（OpenAM 白名单 depth>1 短路绕过，CVSS 9.2）** | 过滤器形同虚设 |
| PHP Laravel/Symfony/ThinkPHP | CVE-2018-15133 等 | POP 链 RCE |
| RubyGems | Gem::SpecFetcher→Runtime 链（2024） | Marshal.load RCE |
| .NET ViewState / BinaryFormatter | 无 machineKey 验证 | RCE |
| 恶意 pickle 工具 | **CVE-2025-1716（PickleScan 静态分析绕过）** | 检测规避 |

