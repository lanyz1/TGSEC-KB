## 七、原生反序列化过滤与绕过

### 7.1 防御机制全景
- **JEP 290 / ObjectInputFilter**（Java 9+）：JVM 级反序列化类过滤，模式语法支持黑白名单、深度/字节数/引用数限制
```java
// 示例：拒绝 commons-collections 所有类 + 限制深度
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "!org.apache.commons.collections.*;maxdepth=30;maxbytes=1048576;maxrefs=1000");
ObjectInputFilter.Config.setSerialFilter(filter);
```
- **Look-ahead 反序列化**：SerialKiller / NotSoSerial / Contrast 等，反序列化前预检类
- **resolveClass 重写白名单**：继承 `ObjectInputStream` 重写 `resolveClass` 白名单放行
- **框架级 ClassFilter**：Jenkins JEP-200、WebLogic 黑名单、Shiro 密钥隔离

### 7.2 黑名单绕过思路
1. **等价类替换**：黑名单封 `Transformer` → 换 CB1/ROME/Spring/Hibernate/JDK-only 链
2. **JDK-only 链**：Jdk7u21/Jdk8u20 只用 JDK 类，黑名单一般不会封
3. **不常见包路径**：`com.sun.*`/`sun.*`/`java.*` 内部类常被忽略（如 `sun.reflect.annotation.AnnotationInvocationHandler`、`com.sun.org.apache.xalan...TemplatesImpl`）
4. **替代格式侧迁**：原生被过滤 → 转 XML（XStream）/YAML（SnakeYAML）/JSON（Fastjson）等间接反序列化入口

### 7.3 白名单 / JEP 290 过滤器绕过（2025-2026 最新）
1. **resolveProxyClass 绕过（CVE-2026-47065，CVSS 9.8）**：过滤器不拦截 `TC_PROXYCLASSDESC`（0x7D）代理类描述符的 `resolveProxyClass()` 分派。构造以 `java.lang.reflect.Proxy` 为根的流，接口指向可调用接口 + 内嵌恶意 `InvocationHandler`（如 `AnnotationInvocationHandler`），**绕过 acceptMatchers 白名单**直达 RCE
2. **白名单 depth>1 短路绕过（CVE-2026-62263，OpenAM，CVSS 9.2）**：过滤器若对 `depth > 1` 的对象直接 `ALLOWED`，则白名单只约束根类，嵌套图完全不受检——构造根为被放行类（如 `AuthenticatorImpl`）、内部嵌套完整 Gadget 链即可（readObject 在 cast/断言之前执行）
3. **框架自成员 gadget（CVE-2026-53435，Jenkins）**：过滤器只查类"来自哪里"（core/plugin 命名空间），不查类"做什么"。利用框架自身 `readResolve` 有副作用的类作为 gadget
4. **未覆盖入口**：过滤器只设置在 `ObjectInputStream` 主路径，RMI/JMX/IIOP/Hessian 等其他反序列化入口未设置
5. **Look-ahead 工具只检首类**：SerialKiller/NotSoSerial 若只检查根类，用合法根类包裹深层恶意图绕过
6. **字节流畸形**：修改 serialVersionUID 逃逸校验、垃圾字节填充、利用 `TC_RESET` 重置句柄表规避指纹规则

### 7.4 JDK 版本限制绕过
- JDK 8u191+ 远程 codebase 默认禁用 → 用本地 Gadget 链（CC/CB 等）替代 JNDI 远程类加载
- JDK 8u71+ `AnnotationInvocationHandler` 反序列化受限 → CC1/CC5 失效，改用 CC6/CC7
- JDK 8u251+ BCEL `ClassLoader` 被移除 → BCEL 链失效，改用 TemplatesImpl/文件写入
- JDK 9+ 模块化：`com.sun.*` 默认不可反射 → 需 `--add-exports` 或找未封装类

