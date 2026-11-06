---
name: xss-testing
description: XSS跨站脚本深度测试与利用高级技能：反射/存储/DOM/mXSS/vXSS/Blind/Universal全类型、20+注入上下文矩阵、WAF深度绕过与Hackvertor编码矩阵、CSP高级绕过（script gadget/JSONP/strict-dynamic/Trusted Types对抗）、DOMPurify历史绕过谱系、现代框架（React/Vue/Angular/Svelte）危险Sink审计、DOM Clobbering与原型污染链式XSS、Service Worker持久化、XSS→CSRF→账户接管完整链、AI大模型辅助生成polyglot与盲打自动化、BeEF浏览器后渗透
version: 3.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='xss-testing', file_path='references/full.md')`

# XSS跨站脚本深度测试与利用技能（v3.0）

测绘引擎作业层：`docs/playbooks/测绘引擎XSS作业手法.md`。  
先 `core_web_surface_probe`，验收是脚本在目标源执行，不是 alert。

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、XSS完整攻击面与威胁建模](references/split-02-xss.md)
- [二、上下文感知Payload生成](references/split-03-payload.md)
- [三、WAF深度绕过与Hackvertor编码矩阵](references/split-04-waf-hackvertor.md)
- [四、CSP高级绕过（script gadget/JSONP/strict-dynamic/Trusted Types对抗）](references/split-05-csp-script-gadget-jsonp-strict-dynamic-t.md)
- [五、现代框架XSS与危险Sink审计](references/split-06-xss-sink.md)
- [六、DOM XSS深度：Source-Sink审计方法论](references/split-07-dom-xss-source-sink.md)
- [七、mXSS深度：DOMPurify历史绕过全谱系](references/split-08-mxss-dompurify.md)
- [八、DOM Clobbering与原型污染链式XSS](references/split-09-dom-clobbering-xss.md)
- [九、Service Worker/Web Worker持久化与浏览器漏洞利用面](references/split-10-service-worker-web-worker.md)
- [十、高级利用与后渗透（Cookie窃取/键盘记录/钓鱼/BeEF联动）](references/split-11-cookie-beef.md)
- [十一、XSS→CSRF→账户接管（ATO）完整攻击链](references/split-12-xss-csrf-ato.md)
- [十二、AI大模型结合XSS攻防（2025-2026前沿）](references/split-13-ai-xss-2025-2026.md)
- [十三、工具链](references/split-14-section.md)
- [十四、XSS测试检查清单](references/split-15-xss.md)
- [十五、修复建议](references/split-16-section.md)
- [注意事项](references/split-17-section.md)
- [真源](references/split-18-section.md)
- [2026-10 情报批增量（基因突变法 + 隐藏元素 + 组件注入）](references/split-19-2026-10.md)
