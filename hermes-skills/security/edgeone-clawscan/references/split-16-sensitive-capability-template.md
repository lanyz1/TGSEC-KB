## Sensitive Capability Template

If the skill has elevated permissions or sensitive capabilities, but the current static check does not show clear malicious use, answer in the user's detected language using the style below.

Chinese example: `发现需关注项，但当前未见明确恶意证据。这个 skill 具备{已确认的高权限能力或敏感访问}，主要用于完成它声明的{功能或流程}；建议仅在确认来源可信、权限范围可接受时使用。`
English example: `Needs attention, but no clear malicious evidence found. This skill has {confirmed elevated permissions or sensitive access}, primarily used to complete its declared {function or workflow}. Use only when the source is trusted and the permission scope is acceptable.`

Use this template with the following rules:
- `{confirmed elevated permissions or sensitive access}` — only list confirmed capabilities (e.g. "system command execution", "file access outside workspace", "network requests", "sensitive config access").
- `{function or workflow}` — only use the purpose stated in `SKILL.md`; do not add your own interpretation.
- Only mention specific capabilities such as API key read/write, environment variable access, or bash execution when there is clear evidence.


