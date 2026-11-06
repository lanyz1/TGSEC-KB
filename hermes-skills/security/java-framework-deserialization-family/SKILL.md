---
name: java-framework-deserialization-family
description: "Java框架漏洞利用时使用。触发: Spring, Shiro, Fastjson, 内存马。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, java, spring, shiro, fastjson, deserialization, memory-shell, surveyengine-absorbed]
    related_skills: [web-deserialization, heapdump-credential-hunter, server-getshell-playbook, surveyengine-knowledge-pack]
---

# Java 框架漏洞深度利用家族(Spring/Shiro/Fastjson)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。**三卡全文在镜像**(各 1000-1700 行,含 2025-2026 全 CVE 细节/完整 payload 库/内存马源码):
- `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\spring-exploitation\SKILL.md`(1692 行)
- `...\shiro-exploitation\SKILL.md`(1261 行)
- `...\fastjson-exploitation\SKILL.md`(1166 行)
本卡 = 决策矩阵 + 核心打法,遇到具体版本/场景翻镜像全文。

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

## 2. Shiro 家族(核心决策)

### 指纹
- 响应头 `rememberMe=deleteMe`(未登录访问受限页)→ 存在 Shiro
- Cookie: `rememberMe` Base64 AES 加密序列化

### rememberMe 加密模式
- **CBC**: Shiro <1.4.2, IV=密钥前 16 字节(→ 固定 IV)
- **GCM**: Shiro ≥1.4.2, 随机 IV(更安全)
- 默认 Key: `kPH+bIxk5D2deZiIxcaaaA==`(1.2.4 前硬编码,大量沿用)

### 攻击决策
1. **密钥爆破**: 送 `rememberMe=<Base64(AES(key, serialized))>`;响应 deleteMe 变化 = 密钥对
   - 工具: shiro_attack / ShiroExploit / ysoserial 配套;高频字典 250+ 条(镜像 §3.5)
   - CBC 模式密钥不可知 → **Shiro-721 Padding Oracle**(工具: shiro_exp / shiro-721)
2. **Gadget 链**: CommonsBeanutils1(最佳经典链)→ 版本/JDK 兼容矩阵见镜像 §4.3
3. **认证绕过家族**(CVE-2020-1957 → CVE-2026-56091): URL 路径解析差异 `;/`、`..;/`、`%3b`、双写斜杠 → 未授权直达
4. **组合**: Shiro+Fastjson/Log4j、Shiro + Spring Boot 生态
5. **回显/不出网**: 错链回显、Tomcat 内存马(镜像 §5)

## 3. Fastjson 家族(核心决策)

### 指纹
- `{"@type":"java.lang.Class"...}` 报错/超时差异;`fastjson` 版本号在报错/响应差异
- 区分 Fastjson1 vs 2: `{"@type":"java.lang.AutoCloseable"}` 响应差异

### AutoType 绕过时间线
| 版本 | 绕过 | 手法 |
|---|---|---|
| ≤1.2.24 | 无限制 | 直接 @type + JNDI |
| 1.2.25-41 | L 前缀 | `Lcom.sun.rowset.JdbcRowSetImpl;` |
| 1.2.25-42 | 双写 | `LLcom...;;` |
| 1.2.25-43 | 方括号 | `[com.sun...` |
| 1.2.25-47 | 缓存通杀 | java.lang.Class 缓存绕过 checkAutoType |
| 1.2.68+ | expectClass | 二次解析绕过(到 1.2.83) |
| **1.2.83** | **Gadget-free RCE** | CVE-2026-16723(镜像 §三.6) |
| **Fastjson2** | **FNV-1a 哈希碰撞** | QVD-2026-45876(镜像 §) |

### 利用链选择(不出网优先)
| 链 | 场景 |
|---|---|
| JNDI | 出网首选(JdbcRowSetImpl) |
| BCEL ClassLoader | 不出网 |
| TemplatesImpl | 不出网(需 parseObject) |
| c3p0 WrapperConnectionPoolDataSource | 不出网 |
| MySQL Connector | 文件读写/RCE |
- **SafeMode**(1.2.68+ 全局开关)= 唯一有效阻断,开启则放弃 AutoType 面

## 4. 通用 Java 反序列化补充
- 走 `web-deserialization` 技能(ysoserial gadget 全谱)
- 打穿后: heapdump 抽凭据 → 内存马持久化(见 heapdump-credential-hunter)

## Pitfalls
- 别只扫 /actuator/health 就结案(只证明存在,不利用)
- heapdump 别只 strings 扫字节(可能漏对象图内凭据)→ 用 jar 工具拆对象图
- Shiro 爆破密钥: 判断信号是 deleteMe 有无,不是响应码
- Fastjson: 高版本先试缓存绕过/expectClass,别一上来旧 payload
- 2026 CVE 情报在镜像卡里最全(spring AI/cloud config 批量、shiro 新认证绕过、fastjson2 碰撞),实战前翻镜像
