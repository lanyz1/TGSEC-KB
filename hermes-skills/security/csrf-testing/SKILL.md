---
name: csrf-testing
description: CSRF跨站请求伪造高级攻防专业技能：GET/POST/JSON/Flash/SOAP全请求类型、CSRF Token绕过矩阵、SameSite跨浏览器绕过(Lax+POST窗口/方法覆盖/CSWSH)、双提交Cookie绕过、CORS+CSRF链式利用与Token泄露、登录CSRF与OAuth授权码CSRF(账户劫持)、WebSocket/GraphQL/REST状态改变API、Service Worker劫持与缓存投毒、CSPT2CSRF、CSRF→账户接管→业务影响完整攻击链、AI大模型辅助PoC生成与Token校验逻辑审计
version: 3.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='csrf-testing', file_path='references/full.md')`

# CSRF跨站请求伪造深度攻防测试技能

<!-- split-index -->

## Section index

- [作业入口（先跑这个）](references/split-01-section.md)
- [概述](references/split-02-section.md)
- [一、CSRF完整攻击面与威胁建模](references/split-03-csrf.md)
- [二、检测方法论](references/split-04-section.md)
- [三、基础利用技术（全请求类型）](references/split-05-section.md)
- [四、CSRF Token绕过矩阵（深化）](references/split-06-csrf-token.md)
- [五、SameSite Cookie语义与跨浏览器绕过](references/split-07-samesite-cookie.md)
- [六、Referer/Origin校验绕过](references/split-08-referer-origin.md)
- [七、双提交Cookie绕过与Cookie注入](references/split-09-cookie-cookie.md)
- [八、CORS+CSRF链式利用与Token泄露通道](references/split-10-cors-csrf-token.md)
- [九、登录CSRF与OAuth授权码CSRF（账户劫持级）](references/split-11-csrf-oauth-csrf.md)
- [十、状态改变类API CSRF（WebSocket/GraphQL/REST）](references/split-12-api-csrf-websocket-graphql-rest.md)
- [十一、Service Worker劫持与缓存投毒CSRF](references/split-13-service-worker-csrf.md)
- [十二、CSRF→账户接管→业务影响完整攻击链](references/split-14-csrf.md)
- [十三、AI大模型结合攻防](references/split-15-ai.md)
- [十四、自动化工具链](references/split-16-section.md)
- [十五、CSRF测试检查清单](references/split-17-csrf.md)
- [十六、修复建议](references/split-18-section.md)
- [注意事项](references/split-19-section.md)
- [SRC 猎手补充手法](references/split-20-src.md)
- [真源](references/split-21-section.md)
