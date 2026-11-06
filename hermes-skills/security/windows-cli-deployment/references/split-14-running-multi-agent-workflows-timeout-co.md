## Running Multi-Agent Workflows (Timeout Considerations)

Multi-agent workflows with parallel sub-agents can take **6-10+ minutes** (security-audit: 10m9s, 51 agents, 957k tokens). When running through `execute_code` (Python sandbox), the sandbox has a **300s (5 minute) hard execution timeout** — this is an infra-level limit, not configurable via `timeout=` in subprocess. Even calling `subprocess.run(..., timeout=600)` inside `execute_code` WILL be killed at 300s by the sandbox itself.

**This is a critical constraint to plan for.** A 3-phase workflow with just 4 parallel Sonnet 4-6 agents exceeded the 300s limit (survey ~60s + deep-dives ~120-180s + compile ~30s = 210-270s base, but parallel agents with schema mode can balloon unpredictably).

**Options for long-running workflows:**
1. **Use background terminal processes** — start the wf-engine in the background and poll for results
2. **Use simpler workflows** — reduce parallel agents, smaller max_turns
3. **Split into phases** — run decompose first, then harvest with collected subtasks
4. **Accept the timeout** — some workflows will produce partial output before timeout kills them (check `~/.wf-engine/runs/` for partial snapshots)

The wf-engine supports `--resume RUNID` to resume interrupted runs from the last completed agent, but this feature hasn't been tested on this setup.

### Per-Agent Model Selection

You can specify a **different model per sub-agent** via the `model` option in `agent()`:

```javascript
const result = await agent(
  'Complex analysis task',
  { label: 'deep-dive', model: 'claude-opus-4-6' }  // overrides default
)
```

This is useful for: using a cheap model (Haiku/Sonnet) for survey/parse phases and an expensive model (Opus) only for deep analysis phases.

The default model is set at the CLI level: `--model claude-sonnet-4-6`.

