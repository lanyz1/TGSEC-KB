## Required Output Style

- Answer in the same language the user used in their request (see **Language Detection Rule**); default to Chinese if the language cannot be determined.
- Default to one sentence or one short paragraph.
- Do not print the Feature 1 report header, configuration audit table, installed-skills table, or vulnerability table.
- Do not expand a single-skill question into a full OpenClaw system review.
- Mention only the result for the asked skill unless the user explicitly asks for more breadth.
- Avoid absolute wording such as `绝对安全`、`可放心使用`、`已彻底解决`、`没有任何风险`.
- When no confirmed Medium+ findings exist, make it clear that the conclusion is limited to the current static check scope and does not cover unknown, future, or runtime-triggered risks.

