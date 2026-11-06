## 概述

反序列化漏洞（CWE-502）发生在应用程序将不受信任的数据还原为对象时：Java 的 `readObject()`、PHP 的 `unserialize()`、Python 的 `pickle.loads()`、.NET 的 `BinaryFormatter` 在"还原对象"过程中会执行类自身代码（`readObject`/魔术方法/opcode），攻击者通过构造恶意字节流串联既有类库方法调用（Gadget 链 / POP 链），最终直达 `Runtime.exec()`、`system()`、`eval()` 等危险 Sink 实现 RCE。本技能从资深攻防专家视角，系统化覆盖**攻击面识别 → Gadget 挖掘方法论 → 各语言利用链深度分析 → 过滤器绕过 → AI 框架反序列化面 → AI 辅助攻防 → 不出网利用与回显 → 内网渗透 → 修复加固**完整攻防闭环，并同步 2025-2026 年最新利用链与 CVE 情报。

### 核心概念
- **Gadget 链（Java）**：反序列化入口（`readObject`/`readResolve`）→ 串联 classpath 中既有类的方法调用 → 最终触发危险操作。攻击者不注入新代码，只是"编排"已有类
- **POP 链（PHP）**：Property-Oriented Programming，利用魔术方法（`__destruct`/`__wakeup`/`__toString` 等）串联方法调用
- **pickle 是栈式虚拟机**：Python pickle 不是数据格式而是指令序列（opcode），反序列化即执行，`__reduce__`/`find_class` 是核心利用原语
- **原生 vs 间接反序列化**：原生（Java 序列化协议/PHP serialize/pickle）与间接（JSON/YAML/XML 解析器中的类型标记机制，如 Fastjson `@type`、Jackson `@class`、SnakeYAML `!!`）
- **过滤器（JEP 290/ObjectInputFilter）**：Java 9+ 的类级黑白名单过滤，但存在多种绕过（见第七章）
- **信任边界**：任何"数据→对象"转换都应在信任边界被审视，序列化数据本身不可信

### 安全演进时间线
| 阶段 | 时间 | 标志性事件 | 攻防要点 |
|------|------|-----------|---------|
| 启蒙期 | 2011-2015 | JRE8u20/7u21 链发布；CC 链被公开 | 反序列化可 RCE 进入大众视野 |
| 爆发期 | 2015-2016 | Apache Commons Collections CVE-2015-7501；ysoserial 发布；WebLogic CVE-2015-4852；Shiro CVE-2016-4437 | 企业中间件批量沦陷，黑名单式修复出现 |
| 绕道期 | 2017-2019 | JEP 290 (Java 9)；Jackson/Fastjson AutoType 绕过；SnakeYAML/PyYAML 链 | 过滤器/黑名单被不断绕过，expectClass、JDK-only 链出现 |
| 扩展期 | 2020-2023 | Log4Shell (CVE-2021-44228)；XStream 系列；ysoserial.net 成熟 | JNDI 注入成为通用武器，JDK 8u191+ 后转向本地 Gadget |
| 工程化期 | 2023-2025 | Gadget 自动化挖掘工具链（CodeQL/Semgrep 规则、链式搜索）；AI 辅助漏洞挖掘兴起 | 静态分析 + 语义搜索取代纯手工挖链 |
| AI 框架期 | 2024-2026 | vLLM CVE-2025-32444 (CVSS 10.0)；LangChain CVE-2025-68664 (lc 键序列化注入)；PyTorch weights_only 绕过 CVE-2025-32434；MCP STDIO 设计级 RCE；JEP 290 绕过 CVE-2026-47065 | LLM 推理/向量库/MCP 成为新反序列化攻击面，提示注入成为前置攻击向量 |

