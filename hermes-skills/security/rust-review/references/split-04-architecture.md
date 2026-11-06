## Architecture

```
coordinator: context.md → build_run_plan.py → TaskCreate × M
 → primer (foreground) → M workers (parallel) → classify outcomes
 → dedup-judge → fp-judge → SARIF+REPORT.md → return
```

Output: `context.md`, `plan.json`, `worker-prompts/`, `findings/`, `findings-index.d/`, `findings-index.txt`, `coverage/`, `run-summary.md`, `dedup-summary.md`, `fp-summary.md`, `REPORT.md`, `REPORT.sarif`.

### Path Resolution

Resolve `RUST_REVIEW_PLUGIN_ROOT` — must contain `prompts/clusters/unsafe-boundary.md`. Try: `${CLAUDE_PLUGIN_ROOT}` → `${CODEX_PLUGIN_ROOT}` → `find ~/.claude ~/.codex . -path '*/plugins/rust-review/prompts/clusters/unsafe-boundary.md' -print -quit`. Abort if unresolved.

### Scope Convention

- `finding_scope_root` — audit subtree; findings only here
- `context_roots` — read-only inspection (default `.`); reading outside scope OK, filing findings not

---

