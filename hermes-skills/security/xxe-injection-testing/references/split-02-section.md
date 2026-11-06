## 概述

XXE（XML External Entity Injection）利用 XML 解析器对外部实体的不安全处理，实现**任意文件读取、SSRF、内网端口扫描、RCE（特定场景）、DoS**。尽管自 2017 年起常驻 OWASP Top 10，2025-2026 年仍持续爆发高危害漏洞（Apache Tika CVSS 10.0、GeoServer、Struts、fast-xml-parser 系列、LangChain AI 组件等），是**挖洞/红队实战中性价比最高的入口漏洞之一**。本技能 v3.0 站在资深攻防专家视角，从"检测利用"升级为"**攻击面测绘 → 防护绕过 → 深度利用 → 内网渗透 → 前沿情报 → AI 加持**"的完整方法论。

### 核心概念
- **DTD 与实体**：XML 文档顶部的 `<!DOCTYPE>` 可声明实体（Entity），实体分内部实体（值内联）与外部实体（`SYSTEM` 指向外部资源）
- **外部实体**：`<!ENTITY xxe SYSTEM "file:///etc/passwd">`，解析时解析器主动拉取资源——XXE 根源
- **参数实体**：`<!ENTITY % p "值">`，只能在 DTD 内部用 `%p;` 引用，是 Blind XXE 外带的基石
- **通用实体**：`<!ENTITY xxe "值">`，在文档正文用 `&xxe;` 引用，有回显场景的关键
- **XInclude**：`<xi:include href="..."/>`，**无需 DOCTYPE** 即可包含外部文件/URL，绕过"禁用 DTD"防护
- **外部 DTD 与内部 DTD**：OOB 外带必须用外部 DTD（内部 DTD 中参数实体引用参数实体受限）
- **解析器安全配置**：`disallow-doctype-decl` / `external-general-entities` / `external-parameter-entities` / `load-external-dtd` / `XIncludeAware` 五要素

### 安全演进时间线
| 阶段 | 时间 | 关键事件 | 攻防要点 |
|------|------|---------|---------|
| 蛮荒期 | 2002 | Steuck 发现 XXE | 直接 `<!ENTITY SYSTEM>` 读文件 |
| 普及期 | 2013-2017 | Google/Facebook/Apple 相继中招，OWASP Top 10 | 各语言解析器默认开启外部实体 |
| 修复期 | 2017-2023 | 现代框架默认加固（libxml2 2.9+/PHP 8.0+/.NET 4.5.2+） | 攻击面转向**遗留系统、第三方库、文档解析链、配置不彻底** |
| 新载体期 | 2023-2024 | CosmicSting(CVE-2024-34102)、SharePoint(CVE-2024-30043) | 电商、办公套件大规模 XXE RCE |
| 2025-2026 爆发期 | 2025-2026 | Apache Tika(CVE-2025-66516 CVSS 10)、GeoServer(CVE-2025-58360)、Apache CXF(CVE-2026-65432)、fast-xml-parser(CVE-2026-25896/33036)、LangChain(CVE-2025-6985) | **文档解析管线、JS XML 库、AI 应用成为新主战场** |

