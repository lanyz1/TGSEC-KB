## Orchestration Phases

### Phase 0: Parameter Collection

Required: `threat_model` (REMOTE/LOCAL_UNPRIVILEGED/BOTH), `worker_model` (haiku/sonnet/opus), `severity_filter` (all/medium/high), `scope_subpath` (optional). One `AskUserQuestion` for unresolved params.

### Phase 1: Prerequisites

Confirm `uv` present. Probe `${finding_scope_root}` for flags:

```bash
find "${finding_scope_root:-.}" -name '*.rs' -print -quit                    # Rust presence
grep -rlE '\bunsafe\s+(extern|fn|impl|trait)\b|\bunsafe\s*\{' --include='*.rs' "${finding_scope_root:-.}" | head -1  # has_unsafe
grep -rlE 'extern\s+"(C|system|stdcall|cdecl)"' --include='*.rs' "${finding_scope_root:-.}" | head -1               # has_ffi
grep -rlE '\b(std::(thread|sync)|parking_lot|crossbeam|rayon|tokio::sync|Atomic)' --include='*.rs' "${finding_scope_root:-.}" | head -1  # has_concurrency
grep -rlE '\basync\s+(fn|move|\{)|\.await\b|tokio::|async_std::' --include='*.rs' "${finding_scope_root:-.}" | head -1  # has_async
grep -rlE '#!?\[repr\([^]]*packed' --include='*.rs' "${finding_scope_root:-.}" | head -1   # has_packed_repr
grep -rlE '\bPathBuf\b|\bPath\b' --include='*.rs' "${finding_scope_root:-.}" | head -1     # has_fs_io
```

Non-empty output → flag true. False-positive flags add harmless workers; false-negative skips passes.

### Phase 2: Output Directory

```bash
mkdir -p "${output_dir}/findings" "${output_dir}/coverage"
```

### Phase 3: Codebase Context

Skim README/Cargo.toml/build.rs (preflight with `find`, not `ls`). Write `${output_dir}/context.md` with YAML frontmatter + Purpose/Scope/Entry points/Trust boundaries/Existing hardening.

### Phase 4: Build Run Plan

```bash
uv run --no-project "${RUST_REVIEW_PLUGIN_ROOT}/scripts/build_run_plan.py" \
 --plugin-root "${RUST_REVIEW_PLUGIN_ROOT}" --output-dir "${output_dir}" \
 --threat-model "${threat_model}" --severity-filter "${severity_filter}" \
 --scope-subpath "${finding_scope_root:-.}" --context-roots "${context_roots:-.}" \
 --has-unsafe "${has_unsafe}" --has-ffi "${has_ffi}" \
 --has-concurrency "${has_concurrency}" --has-async "${has_async}" \
 --has-packed-repr "${has_packed_repr}" --has-fs-io "${has_fs_io}" \
 --max-passes-per-worker 4
```

Produces `plan.json` + `worker-prompts/*.txt`. Never re-derive filtering manually. Typical M: ~13 (safe Rust), ~15 (concurrent), ~23 (full unsafe+FFI+concurrency+async).

### Phase 5: Create Bookkeeping Tasks

One `TaskCreate` per worker from `plan.workers[]`. Orchestrator bookkeeping only — workers have no Task tools.

### Phase 6: Spawn Workers

**Phase 6a — Cache primer** (if `plan.run.cache_primer == true`): spawn foreground, worker returns `abort: cache primer`. Warms prefix cache.

**Phase 6b — M workers in parallel**: one message per wave of ≤16 `Agent` calls, **foreground only** (no `run_in_background`). Background spawns defeat primer cache. Read `worker-N.txt` verbatim as prompt.

Critical rules:
- **Never** `run_in_background=true` — defeats cache, wastes primer
- **Never** >16 Agent calls per message — harness silently drops excess
- Balance waves (e.g. M=25 → 13+12)
- Pass spawn prompt verbatim from file

### Phase 7: Classify Outcomes

| Match | Outcome | Action |
|-------|---------|--------|
| `worker-N complete:` | Provisional success | Validate artifacts, then mark completed |
| `abort: spawn prompt malformed` / `pre-work budget exceeded` | Non-retryable | Stop run |
| Other `abort:` | Retryable (max 2 attempts) | Clear prefix files, re-spawn |

Validate with:
```bash
uv run --no-project "${RUST_REVIEW_PLUGIN_ROOT}/scripts/validate_artifacts.py" "${output_dir}/plan.json" \
 --worker worker-N --claimed-count worker-N=<count>
```

Build canonical index from disk:
```bash
find "${output_dir}/findings" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort -u > "${output_dir}/findings-index.txt"
```

Write `run-summary.md`. Surface any incomplete/truncated workers prominently.

### Phase 8: Judge Pipeline (SEQUENTIAL)

**Dedup-judge first** → wait for completion → **then fp-judge**. Never in same message (data dependency).

1. `Agent(subagent_type="rust-review:rust-review-dedup-judge", prompt=f"output_dir: {output_dir}")`
2. Confirm `dedup-summary.md` exists
3. `Agent(subagent_type="rust-review:rust-review-fp-judge", prompt=f"output_dir: {output_dir}\nsarif_generator_path: {sarif_path}")`

### Phase 8b: Report Safety Net

```bash
uv run --no-project "${RUST_REVIEW_PLUGIN_ROOT}/scripts/generate_sarif.py" "${output_dir}"
```

Always run. Idempotent. Unjudged findings emitted as `LIKELY_TP`, exempt from severity filter. Guarantee `REPORT.md` exists (orchestrator writes it if judge failed).

### Phase 9: Return Report

Verify success criteria → `Read REPORT.md` → return with artifacts list.

