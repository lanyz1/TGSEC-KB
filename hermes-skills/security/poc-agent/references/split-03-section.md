## 职责范围

本 Agent 负责基于 Phase 4.5 指纹汇总结果（tech_stack 字段），在 POC 库中搜索匹配的已知漏洞 POC，通过 `http_test.py` 发送验证请求并判断漏洞是否存在。

本 Agent **不执行**额外的渗透测试、模糊测试或手动漏洞挖掘；这些工作由其他渗透 Agent 负责。

默认仅使用本地 `public/` 和 `private/` POC。
只有当用户明确要求允许联网搜索 POC 时，才可在本地检索完成后，仅使用本文档内置的默认联网来源，以及 `{SKILL_ROOT}/pocs/POC_SEARCH_SOURCES_USER.md` 中列出的用户自定义来源进行补充搜索。

| 职责 | 说明 |
|------|------|
| 指纹匹配 | 从 `fingerprint.json` 的 `tech_stack` 提取关键字，优先搜索 `{SKILL_ROOT}/pocs/public/` 和 `{SKILL_ROOT}/pocs/private/` 目录中的本地 POC；在用户授权时再补充联网搜索 |
| POC 解析 | 解析本地 Nuclei YAML，或从联网命中的模板、脚本、复现说明中提取等效请求定义和匹配条件 |
| 漏洞验证 | 使用 `{SKILL_ROOT}/scripts/http_test.py` 发送精确请求，验证本地 POC 或联网命中的可执行线索 |
| 结果回填 | 将确认的漏洞写入 `workspace/findings/poc-agent.json` |

