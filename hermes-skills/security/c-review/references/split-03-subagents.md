## Subagents

| Type | Purpose | Tools |
|------|---------|-------|
| `c-review-worker` | Run cluster, write findings | Read, Write, Edit, Bash |
| `c-review-dedup-judge` | Merge duplicates (**first**) | Read, Write, Edit, Glob |
| `c-review-fp-judge` | FP+severity+reports (**second**) | Read, Write, Edit, Bash |

**Bash/Glob exclusion**: Bash-holding agents use `find`/`rg`/`grep` instead of `Glob`/`Grep`. Run regex seeds with `rg`; fallback to `grep -E` with POSIX classes if `rg` absent.

