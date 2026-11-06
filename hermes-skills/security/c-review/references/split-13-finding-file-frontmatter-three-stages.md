## Finding file frontmatter — three stages

Authoritative schema: `agents/c-review-worker.md` ("Finding File Format"). Three-stage write:

1. **Worker** — base fields (`id`, `bug_class`, `title`, `location`, `function`, `confidence`, `worker`) + seven body sections.
2. **Dedup-judge** — adds `merged_into` on duplicates, or `also_known_as` + `locations` on primaries that absorbed.
3. **FP+Severity judge** — adds `fp_verdict` + `fp_rationale` on every primary; on survivors (`TRUE_POSITIVE`/`LIKELY_TP`) also adds `severity`, `attack_vector`, `exploitability`, `severity_rationale`.

