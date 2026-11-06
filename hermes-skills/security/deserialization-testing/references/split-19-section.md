## 修复建议

### 通用原则
- **首选"不反序列化不可信数据"**：用 JSON/Protobuf 等纯数据格式替代原生二进制序列化；传输前做签名/HMAC 完整性验证
- **白名单优于黑名单**：反序列化只允许业务明确需要的类；黑名单永远追不上新链
- **最小化攻击面**：禁用不需要的反序列化服务（RMI/JMX/T3/IIOP），限制出站网络（阻断 LDAP/RMI 出站）
- **依赖治理**：升级存在 CVE 的库（commons-collections 4.5.4+/fastjson2/xstream 高版本/snakeyaml 2.x）；用 SBOM + 漏洞扫描持续监控
- **运行权限最小化**：应用进程低权限运行、容器隔离，降低 RCE 影响面

### Java 专项
```java
// JEP 290 过滤器（注意 resolveProxyClass 绕过，需配合最新 JDK 补丁与 RASP）
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "!org.apache.commons.collections.*;!com.sun.org.apache.xalan.*;maxdepth=30");
ObjectInputFilter.Config.setSerialFilter(filter);
// 或重写 resolveClass 白名单（仅放行业务包）
// 升级 JDK 至最新（修复 CVE-2026-47065 类过滤器绕过）
// 禁用/加固 RMI：-Djava.rmi.server.useCodebaseOnly=true；不监听 1099
// Shiro：自定义强密钥（禁止默认 kPH+bIxk5D2deZiIxcaaaA==）
// WebLogic：打补丁 + 禁用 T3 反序列化黑名单外类
```
- Jackson：`ObjectMapper.enableDefaultTyping` 一律禁用；Fastjson：SafeMode（详见 fastjson-exploitation 技能）
- XStream：升级 + 白名单（`XStream.setupDefaultSecurity` + `addPermission`）

### PHP 专项
- PHP 8+ 保持 `phar.readonly=1` 且不处理不可信 phar；审计 `unserialize()` 输入（加 HMAC/签名）
- Session `serialize_handler` 全局统一（php_serialize）；`session.upload_progress` 等入口防注入
- 禁止 `yaml_parse` 处理不可信输入；禁用 `allow_url_include`

### Python 专项
```python
# PyYAML：一律 yaml.safe_load()
import yaml
data = yaml.safe_load(user_input)
# pickle：拒绝不可信输入；必须使用时继承 Unpickler 白名单 find_class
# torch.load：torch.load(path, weights_only=True) + 升级 PyTorch>=2.6
# 对模型/索引/缓存文件做 picklescan 扫描；Celery 禁用 pickle 序列化器
```

### .NET 专项
- 保持 .NET 8+ BinaryFormatter 默认禁用；迁移 XmlSerializer/DataContractSerializer/Json.NET（TypeNameHandling=None）
- ViewState：enableViewStateMac=true + 强 MachineKey + ViewStateUserKey
- 对 LegacyBinaryFormatter 调用点做清单管理（列出所有历史用法逐一迁移）

### AI 框架专项
```
- langchain-core 升级 >= 0.3.81 / 1.2.5（CVE-2025-68664）；langgraph-checkpoint >= 3.0
- 禁止对不可信内容调用 load()/loads()；secrets_from_env 保持 False
- vLLM >= 0.8.5（CVE-2025-32444）；KV 传输 socket 仅绑定内网；mooncake 默认关闭
- PyTorch >= 2.6；模型权重来源校验（签名/可信仓库）
- MCP：STDIO 命令白名单、服务器沙箱、外部配置视为不可信、工具调用人工审批
- 向量库/索引/checkpoint 存储视为可信边界内资产，外部写入需验证
```

### WAF / 检测层
- 规则特征：`rO0AB`/`AC ED 00 05`、`@type`、`!!python/object`、`_$$ND_FUNC$$_`、`${jndi:`、`O:\d+:"`
- 异常检测：序列化数据超长、嵌套深度异常、类名黑名单命中、反序列化调用栈监控
- RASP：hook 危险反序列化入口（readObject/unserialize/pickle.loads/Deserialize）阻断执行链

