---
name: deserialization-testing
description: 反序列化漏洞深度攻防专业技能：Java原生反序列化(JRMP/RMI/IIOP)、CommonsCollections全链与版本兼容矩阵、TemplatesImpl深度分析、JEP 290/ObjectInputFilter过滤绕过(CVE-2026-47065)、PHP POP链构造实战、Python pickle利用面(含PyYAML/ruamel/torch.load)、AI大模型框架反序列化面(LangChain CVE-2025-68664/vLLM/PyTorch/MCP)、Gadget挖掘方法论、AI辅助攻防、反序列化→RCE→内网渗透完整链、不出网利用与回显技术、多语言工具链与WAF对抗
version: 3.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='deserialization-testing', file_path='references/full.md')`

# 反序列化漏洞深度攻防技能

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、反序列化攻击面全景](references/split-02-section.md)
- [二、Gadget 挖掘方法论](references/split-03-gadget.md)
- [三、Java 原生反序列化深度](references/split-04-java.md)
- [四、CommonsCollections 全链与版本兼容矩阵](references/split-05-commonscollections.md)
- [五、TemplatesImpl 与其他核心 Gadget 深度](references/split-06-templatesimpl-gadget.md)
- [六、Java 主流中间件反序列化链](references/split-07-java.md)
- [七、原生反序列化过滤与绕过](references/split-08-section.md)
- [八、PHP 反序列化 POP 链构造实战](references/split-09-php-pop.md)
- [九、Python pickle 利用面](references/split-10-python-pickle.md)
- [十、AI 大模型框架反序列化面（2025-2026 新攻击面）](references/split-11-ai-2025-2026.md)
- [十一、AI 大模型结合：AI 辅助反序列化攻防](references/split-12-ai-ai.md)
- [十二、.NET 反序列化](references/split-13-net.md)
- [十三、Ruby / Node.js / Go 反序列化](references/split-14-ruby-node-js-go.md)
- [十四、反序列化→RCE→内网渗透完整链](references/split-15-rce.md)
- [十五、检测与验证](references/split-16-section.md)
- [十六、工具链表](references/split-17-section.md)
- [检查清单](references/split-18-section.md)
- [修复建议](references/split-19-section.md)
- [注意事项](references/split-20-section.md)
- [真源](references/split-21-section.md)
- [When to Use](references/split-22-when-to-use.md)
- [1. Spring 家族(核心决策)](references/split-23-1-spring.md)
- [2. Shiro 家族(核心决策)](references/split-24-2-shiro.md)
- [3. Fastjson 家族(核心决策)](references/split-25-3-fastjson.md)
- [4. 通用 Java 反序列化补充](references/split-26-4-java.md)
- [Pitfalls](references/split-27-pitfalls.md)
- [参考文件](references/split-28-section.md)
