## Rationalizations to Reject

- **"Background spawns parallelize the workers."** They do not — `Agent` calls in a single assistant message already run concurrently. `run_in_background=true` defeats the Phase 6a primer cache, so every worker pays full cache-creation (`cache_read_input_tokens=0`) and the ~15 K-token primer is wasted M times. This is the single most common defect — multiple recent runs spawned 7-of-8 (or all) workers with `bg=true`. Default: omit `run_in_background` from worker spawns.
- **"I'll re-derive the cluster list / paths / pass prefixes inline instead of running `build_run_plan.py`."** The script is the only authority for selection and rendering. Paraphrasing it drops fields that the worker self-check requires, producing `worker-N abort: spawn prompt malformed`. Always run the script and `Read plan.json`.
- **"The run partially succeeded — I'll just write `REPORT.md` from what completed."** Hiding partial runs behind a successful report is a correctness bug. If any Phase-5 cluster task is not `completed`, surface it prominently in `run-summary.md` and the final response.
- **"Zero findings — skip Phase 8."** Always run both judges and Phase 8b: dedup-judge writes a minimal no-op `dedup-summary.md` on an empty index, fp-judge writes empty `REPORT.md`/`REPORT.sarif`, and Phase 8b's SARIF generator emits `results: []` for the empty case. SARIF consumers depend on a stable artifact set.
- **"`Bash: ls README*` is fine for the preflight."** Under zsh, an unmatched glob aborts the whole compound command before `2>/dev/null` runs. Use `find` (never fails on no-match) — and not `Glob`, which is unavailable to an agent that also holds `Bash`.

---

