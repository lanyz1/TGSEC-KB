## Orchestration Phases

### Phase 0: Parameter Collection

Required: `threat_model` (REMOTE/LOCAL_UNPRIVILEGED/BOTH), `worker_model` (haiku/sonnet/opus), `severity_filter` (all/medium/high), `scope_subpath` (optional). One `AskUserQuestion` for unresolved params.

### Phase 1: Prerequisites

Confirm `uv` present. Probe `${finding_scope_root}` for flags:

```bash
find "${finding_scope_root:-.}" -type f \( -name '*.cpp' -o -name '*.cxx' -o -name '*.cc' -o -name '*.hpp' \) -print -quit  # is_cpp
grep -rlE '#include[[:space:]]*<(pthread|signal|sys/(socket|stat)|unistd|errno)\.h>' --include='*.c' --include='*.h' --include='*.cpp' "${finding_scope_root:-.}" | head -1  # is_posix
grep -rlE '#include[[:space:]]*<(windows|winbase|winnt|winsock)\.h>' --include='*.c' --include='*.h' --include='*.cpp' "${finding_scope_root:-.}" | head -1  # is_windows
```

Also probe `compile_commands.json` (informational). If absent, suggest CMake `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`.

### Phase 2: Output Directory

```bash
mkdir -p "${output_dir}/findings" "${output_dir}/coverage"
```

### Phase 3: Codebase Context

Skim README/Makefile/CMakeLists.txt (preflight with `find`, never `ls` — zsh glob abort). Write `${output_dir}/context.md` with YAML frontmatter + Purpose/Scope/Entry points/Trust boundaries/Existing hardening.

### Phase 4: Build Run Plan

```bash
uv run --no-project "${C_REVIEW_PLUGIN_ROOT}/scripts/build_run_plan.py" \
 --plugin-root "${C_REVIEW_PLUGIN_ROOT}" --output-dir "${output_dir}" \
 --threat-model "${threat_model}" --severity-filter "${severity_filter}" \
 --scope-subpath "${finding_scope_root:-.}" --context-roots "${context_roots:-.}" \
 --is-cpp "${is_cpp}" --is-posix "${is_posix}" --is-windows "${is_windows}" \
 --max-passes-per-worker 4
```

Produces `plan.json` + `worker-prompts/*.txt`. Never re-derive manually. Typical M: 13 (C POSIX), 15 (C++ POSIX), 18 (C++ POSIX+Windows). `buffer-write-sinks` consolidated cluster (13 passes) never chunked.

### Phase 5: Create Bookkeeping Tasks

One `TaskCreate` per worker. Orchestrator bookkeeping only.

### Phase 6: Spawn Workers

**Phase 6a — Cache primer** (if enabled): spawn foreground, warms prefix cache.

**Phase 6b — M workers in parallel**: ≤16 per wave, **foreground only**.

Critical rules:
- **Never** `run_in_background=true` — defeats cache
- **Never** >16 Agent calls per message
- Pass `worker-N.txt` verbatim as prompt

### Phase 7: Classify Outcomes

| Match | Outcome | Action |
|-------|---------|--------|
| `worker-N complete:` | Provisional success | Validate, mark completed |
| `abort: spawn prompt malformed` / `pre-work budget exceeded` | Non-retryable | Stop |
| Other `abort:` | Retryable (max 2) | Clear prefix files, re-spawn |

Validate:
```bash
uv run --no-project "${C_REVIEW_PLUGIN_ROOT}/scripts/validate_artifacts.py" "${output_dir}/plan.json" \
 --worker worker-N --claimed-count worker-N=<count>
```

Build index:
```bash
find "${output_dir}/findings" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort -u > "${output_dir}/findings-index.txt"
```

### Phase 8: Judge Pipeline (SEQUENTIAL)

Dedup-judge **first** → confirm `dedup-summary.md` → **then** fp-judge. Never same message.

### Phase 8b: Report Safety Net

```bash
uv run --no-project "${C_REVIEW_PLUGIN_ROOT}/scripts/generate_sarif.py" "${output_dir}"
```

Always run. Unjudged findings as `LIKELY_TP`, exempt from filter. Guarantee `REPORT.md` exists.

### Phase 9: Return Report

Verify success criteria → return `REPORT.md` + artifacts list.

