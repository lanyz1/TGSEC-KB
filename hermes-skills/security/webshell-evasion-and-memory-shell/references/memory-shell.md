# Java 内存马（无文件驻留）

目标：**不落地文件**的 webshell —— 请求进来时执行，进程重启即消失（除非配合 Agent/持久化）。
演进：文件马 → 流量加密马 → 内存马（Servlet/Filter/Listener/Interceptor/Valve/Agent）。

## 六类注册点（Tomcat / Spring）

| 类型 | 注册点（关键 API） | 触发时机 |
|------|-------------------|----------|
| Servlet | `StandardContext.addServletMappingDecoded` + wrapper 绑定 servlet 实例；或 `ServletContext.addServlet` | 任意 URI 命中该路径 |
| Filter | `StandardContext.addFilterDef` + `addFilterMap` + 注册 `ApplicationFilterConfig` 到 `filterConfigs` | **每个请求**都过（最稳） |
| Listener | `StandardContext.addApplicationEventListener` / `addApplicationLifecycleListener`（`ServletRequestListener#requestInitialized`） | 请求进入时 |
| Spring Interceptor | `RequestMappingHandlerMapping#getAdaptedInterceptors()` 加自定义 `HandlerInterceptor`；或动态注册 Controller | 请求被 DispatcherServlet 处理时 |
| Valve（Tomcat 专有） | `StandardContext.getPipeline().addValve(new ValveBase(){...})` | 请求进 pipeline 时（更底层、不易被 Filter 遍历发现） |
| Java Agent | `premain/agentmain` + `Instrumentation.retransformClasses` 改已有类字节码 | 进程级，可跨重启（需另存 jar/注入） |

## 注入方式（有入口才有内存马）

```text
① 反序列化链：CC / Fastjson / Shiro / Weblogic T3 → 反射注册 Filter/Servlet
② 表达式注入：SpEL / OGNL / Groovy → 执行注册代码
③ 文件马转内存马：先落一个 JSP 干活，注册完内存马后删文件
④ 上传 jar / 依赖替换 → Agent 方式（attach 或启动参数）
⑤ 已有 shell 时直接 JVM attach：VirtualMachine.attach(pid) + loadAgent
```

现成工具：哥斯拉/冰蝎的内存马模块（Listener/Filter/Servlet/Interceptor/Agent）、
自写 Generator（推荐，工具默认马同样有特征）。

## 最小可用骨架（Filter 思路）

```java
// 关键点：拿 StandardContext → addFilterDef/addFilterMap → filterConfigs 里塞 ApplicationFilterConfig
// 执行体从 request 参数/Header 取，AES 解密后反射调用，输出回写 response
Field ctxField = request.getClass().getField("request");      // RequestFacade → Request
StandardContext ctx = (StandardContext)((Request)ctxField.get(request)).getContext();
```

## 验证判据（必须全过，否则不算内存马）

```text
① 无文件：注册前后对比 web 根目录/临时目录，确认没有新增可执行文件
② 生效：用新路径/新参数触发命令执行，拿到回显
③ 隐蔽：`?param=` 无参访问不报错、不带特征字（如 pass/cmd 这类名字换成正常业务参数）
④ 存活边界：重启 Tomcat → 失效（纯内存）／仍生效（说明有文件或 Agent 持久化，要如实写）
⑤ 清点：记录注册点（哪一类、哪个 URI/参数），用于后续查杀与复检
```

## 交接

| 场景 | 走 |
|------|-----|
| 注入入口是反序列化 | `java-framework-deserialization-family` |
| 目标是 Tomcat/Struts2/Jenkins | `middleware-parser-and-legacy-cve-family` |
| 需要查杀/取证 | `references/detect-and-kill.md` |
| 静态马免杀 | `references/webshell-evasion.md` |
