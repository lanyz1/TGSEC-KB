## 概述

XSS允许攻击者在受害者浏览器中执行任意JavaScript，是现代Web应用中最普遍也最容易被低估的高危漏洞。2025-2026年，XSS攻防已从"漏洞发现"转向"体系对抗"：CSP（Content-Security-Policy）、Trusted Types、Sanitizer API、框架自动编码、HttpOnly Cookie等多层防御日趋严格，但攻击者通过**mXSS新变体、DOMPurify历史绕过（CVE-2026-0540/2449/49459/66010）、script gadget链、Trusted Types策略滥用、原型污染链式利用、AI生成多态polyglot**等手法不断突破。同时，AI大模型（LLM）正把XSS从"手工绕过"推向"生成式对抗"——GenXSS实验证明GPT-4o生成的payload有80%可绕过ModSecurity默认规则集，XSSGAI基于14437条真实攻击样本训练出88%准确率的多态payload生成器。

本技能v3.0站在资深攻防专家视角，系统化覆盖**威胁建模→上下文注入→WAF绕过→CSP对抗→框架Sink审计→mXSS深度→原型污染链→持久化→账户接管链→AI辅助→后渗透**完整方法论，所有Payload可直接复制使用。

### 核心攻防认知
- **XSS本质是数据与代码的边界混淆**：用户输入被当作代码执行，浏览器无法区分可信代码与恶意代码
- **现代XSS主战场在客户端**：DOM型XSS已是2026年最常见的XSS变体，服务器与WAF完全不可见（payload只存在于URL fragment/postMessage/localStorage）
- **CSP不是万能药**：CSP主要防御脚本执行，不直接防御数据窃取；一旦脚本执行，payload即可在页面上下文中运行
- **缓解不等于修复**：WAF/XSS Filter/消毒器只是"缓解器"，绕过方式随解析器差异无穷无尽；正确修复是上下文感知输出编码+Trusted Types
- **AI让签名WAF失效**：多态payload数量无限，任何基于签名的WAF规则集都会被穷举绕过

### 现代防御体系与绕过路径总览
| 防御层 | 作用 | 攻击者的对应绕过 |
|-------|------|----------------|
| 输入过滤/WAF | 拦截危险字符/标签 | 编码变体、多态payload、HPP、解析器差异 |
| 输出编码 | 上下文感知转义 | 双重编码、mXSS突变、DOM sink绕过服务端 |
| 框架自动编码 | React/Vue等默认转义 | 危险的逃生舱口：dangerouslySetInnerHTML/v-html/{@html} |
| Sanitizer/DOMPurify | HTML消毒 | mXSS、命名空间混淆、DOM clobbering、原型污染（历史CVE谱系） |
| CSP | 限制脚本来源 | script gadget、JSONP端点、strict-dynamic滥用、'unsafe-inline'配置失误 |
| Trusted Types | 强制危险sink使用Trusted对象 | 宽松策略创建、策略名冲突、DOM clobbering |
| HttpOnly/SameSite | 保护Cookie | 不以Cookie为目标，改为ATO链/CSRF/密钥窃取 |
| 同源策略(SOP) | 隔离数据 | 0-click uXSS、浏览器漏洞、postMessage滥用 |

