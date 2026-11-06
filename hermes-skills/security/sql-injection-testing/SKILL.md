---
name: sql-injection-testing
description: SQL注入深度测试专业技能：覆盖全数据库注入面、高级混淆与WAF绕过、分数据库版本定制Payload、AI驱动语义绕过
version: 2.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='sql-injection-testing', file_path='references/full.md')`

# SQL注入深度测试技能

测绘引擎作业层：`docs/playbooks/测绘引擎SQL注入作业手法.md`。  
授权站确认注入后走本库阶梯，不要停在「存在注入」：

```bash
python3 tools/ops/sqlmap_kit.py ladder --url 'https://授权/?id=1' -p id --case <案>
```

`waf_sqli_bypass` 优先于裸 sqlmap。dump 授权内直接做，百万拖号先问。对照 `sqlmap-tamper-kit`。

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、注入点完整攻击面](references/split-02-section.md)
- [二、数据库指纹深度识别](references/split-03-section.md)
- [三、核心注入技术（分类型）](references/split-04-section.md)
- [四、WAF深度绕过方法论](references/split-05-waf.md)
- [五、sqlmap高级Tamper组合使用](references/split-06-sqlmap-tamper.md)
- [六、高级利用场景](references/split-07-section.md)
- [七、AI驱动的智能绕过策略](references/split-08-ai.md)
- [八、工具链与自动化](references/split-09-section.md)
- [九、SQL注入测试检查清单](references/split-10-sql.md)
- [十、绕过验证与报告](references/split-11-section.md)
- [十一、防护建议参考](references/split-12-section.md)
- [注意事项](references/split-13-section.md)
- [真源](references/split-14-section.md)
