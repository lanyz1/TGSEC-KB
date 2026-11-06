---
name: file-upload-testing
description: 文件上传漏洞深度测试专业技能：14种WAF绕过策略、分语言免杀WebShell、解析漏洞全场景、从黑名单绕过到RCE完整攻击链
version: 2.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='file-upload-testing', file_path='references/full.md')`

# 文件上传漏洞深度测试技能

测绘引擎作业层先跑，下面长文当附录：

```bash
python3 tools/ops/upload_forge_probe.py kit --case <案>
```

真源：`docs/playbooks/测绘引擎文件上传作业手法.md`。  
能 `X-SE` 下执行命令才算 L3。`web.config` 不要盖站点根。

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、上传点完整攻击面](references/split-02-section.md)
- [二、探测阶段：上传防护指纹识别](references/split-03-section.md)
- [三、14种绕过策略深度详解](references/split-04-14.md)
- [四、免杀WebShell（Godzilla哥斯拉）](references/split-05-webshell-godzilla.md)
- [五、组合利用链](references/split-06-section.md)
- [六、中间件解析漏洞速查](references/split-07-section.md)
- [七、工具使用](references/split-08-section.md)
- [八、验证与报告](references/split-09-section.md)
- [九、修复建议](references/split-10-section.md)
- [测试清单](references/split-11-section.md)
- [注意事项](references/split-12-section.md)
- [真源](references/split-13-section.md)
- [2026-10 情报批增量（限额/后缀过滤绕过 tips）](references/split-14-2026-10-tips.md)
- [外部库增量（2026-10-11 分享包）](references/split-15-2026-10-11.md)
- [解析器 ACE 弹药清单（目标替我方文件做解析时用）](references/split-16-ace.md)
