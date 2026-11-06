## 1. Spring 家族(核心决策)

### 指纹
- `/actuator` 未授权 → 直接信息泄露甚至 RCE 入口;`/actuator/heapdump` → **heapdump-credential-hunter 技能**
- 报错页含 `Whitelabel Error Page` / `spring` 特征;响应头 `X-Application-Context`

### Actuator 利用链(禁只扫 health)
| 端点 | 利用 |
|---|---|
| /actuator/env | 配置泄露;POST 改属性可 RCE(需 jolokia/restart) |
| /actuator/heapdump | **下堆抽凭据**(见 heapdump-credential-hunter) |
| /actuator/jolokia | logback/JNDI → RCE(CVE-2022-22947 系) |
| /actuator/gateway/routes | Spring Cloud Gateway SpEL RCE |
| /actuator/mappings | 隐藏路由发现 |
- **端点绕过**: 路径变形 `/actuator/..;/env`、`/;/actuator`、大小写、`/actuator%2fenv`、`**` 通配

### SpEL 注入家族(RCE 万金油)
- `#{T(java.lang.Runtime).getRuntime().exec('id')}` — StandardEvaluationContext 可调静态方法
- 攻击面: @Value 注解、参数绑定、Spring Cloud Function (`spring.cloud.function.routing-expression`)、Gateway SpEL、Spring Data 查询
- 2026 新洞: CVE-2026-22738 / CVE-2026-41849~41852(修复=换 SimpleEvaluationContext)

### 关键 CVE 速查
| CVE | 版本 | 打法 |
|---|---|---|
| CVE-2022-22965 (Spring4Shell) | Spring MVC + JDK9+ + Tomcat | 数据绑定 → class.module.classLoader 写 JSP |
| CVE-2022-22947 (Gateway) | Spring Cloud Gateway 3.1.0/3.0.0-3.0.6 | SpEL 路由 RCE |
| CVE-2022-22963 (Cloud Function) | 3.1.6/3.2.2 前 | routing-expression SpEL RCE |
| Log4Shell CVE-2021-44228 | log4j2 | JNDI 注入(Spring Boot 常带) |
| Spring AI RCE (2026) | Spring AI 集成 | LLM 工具调用链攻击(见镜像 §Spring AI) |

### 内存马(无文件落地,重启失效)
- Filter 型最通用 → 注册到 Tomcat/Spring 容器;Servlet/Interceptor/ControllerAdvice/WebFlux 各型见镜像
- 触发: 请求头/参数特定标记;绕 WAF;进程内存中无文件可扫

