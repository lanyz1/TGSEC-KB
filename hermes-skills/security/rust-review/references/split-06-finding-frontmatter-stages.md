## Finding Frontmatter Stages

1. **Worker** — `id`, `bug_class`, `title`, `location`, `function`, `confidence`, `worker` + body
2. **Dedup-judge** — `merged_into` on duplicates, `also_known_as` on primaries
3. **FP-judge** — `fp_verdict`, `fp_rationale`; survivors get `severity`, `attack_vector`, `exploitability`

