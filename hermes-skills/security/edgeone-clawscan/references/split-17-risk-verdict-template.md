## Risk Verdict Template

If confirmed Medium+ risk exists, answer in the user's detected language with one short paragraph covering only:
- verdict
- the main risk in plain language
- a short recommendation

Chinese example: `发现风险，不建议直接安装。这个 skill 会额外执行系统命令并访问未声明的敏感路径，超出了它声称的格式化功能。建议先下线该版本，确认来源和代码后再决定是否使用。`
English example: `Risk detected — direct installation is not recommended. This skill executes system commands and accesses sensitive paths not declared in its description, which exceeds its stated formatting function. Disable this version and verify the source and code before deciding whether to use it.`

If multiple confirmed findings exist, summarize only the highest-impact one or two in plain language unless the user asks for details.

---

# Feature 1 输出规范

执行安全体检报告输出时，严格遵守以下规范。

