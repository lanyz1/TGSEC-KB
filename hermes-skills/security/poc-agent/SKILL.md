---
name: poc-agent
description: >-
  测绘引擎·基于指纹识别结果（tech_stack），优先匹配本地 POC；在用户明确授权时补充联网搜索 POC，并通过 http_test.py 验证已知漏洞。 工作流程：读取
  指纹识别结果 → 提取关键字搜索本地与联网 POC → 整理待验证清单 → 解析 POC 定义 → 构造 http_test.py 命令 → 评估匹配器 → 回填 findin
  gs。
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='poc-agent', file_path='references/full.md')`


> **测绘引擎适配**：本卡的「禁止使用 curl」「必须使用 http_test.py」等工具限制仅在 72stack-sec 独立工作流内生效。
> 在测绘引擎常规作业中，curl / httpx / requests / 本库探针（`*_probe.py`）均可正常使用，不受本卡工具锁定约束。

# poc-agent（测绘引擎）

目标须在 `config/scope*.json`。本库已有专链时专卡赢。

<!-- split-index -->

## Section index

- [真源](references/split-01-section.md)
- [角色身份](references/split-02-section.md)
- [职责范围](references/split-03-section.md)
- [输入数据](references/split-04-section.md)
- [HTTP 发包工具（强制）](references/split-05-http.md)
- [白帽子职业操守（强制遵守）](references/split-06-section.md)
- [POC 验证流程（强制执行）](references/split-07-poc.md)
- [输出格式](references/split-08-section.md)
- [反幻觉规则](references/split-09-section.md)
