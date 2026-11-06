# ReClaude Prompt Passing Workarounds (2026-07-12)

## Problem: Prompt Truncation via `-p` Flag

When passing prompts to ReClaude using `-p "$(cat file)"`, shell variable expansion can cause prompt truncation. This manifests as the model responding "your message got cut off" or "nothing followed."

## Solution: stdin Pipe

Use stdin pipe instead of `-p` flag for complex/long prompts:

```bash
# ✅ WORKS - stdin pipe (preferred for long prompts)
cat prompt.txt | reclaude --model claude-sonnet-4-6 --print

# ❌ FAILS - -p with shell expansion (often truncated)
reclaude -p "$(cat prompt.txt)" --model claude-sonnet-4-6 --print

# ✅ WORKS - -p with short inline string
reclaude -p "Short prompt here" --model claude-sonnet-4-6 --print
```

## wf-engine Agent Data Passing Limitation

When using wf-engine with ReClaude backend (`backend=reclaude-cli`), data passed between agents is often truncated or lost.

**Symptoms**:
- Agent[reader] completes successfully with file content
- Agent[assessor] receives truncated prompt: "your message got cut off"
- agent[reader].done shows tokens used but 0 tool calls

**Root cause**: wf-engine parses ReClaude JSON output (`--output-format json`) and reconstructs the prompt for the next agent. The JSON result parsing or prompt reconstruction introduces truncation for long text.

**Workarounds**:
1. Combine analysis into a single agent (multi-phase not needed)
2. Use direct ReClaude stdin calls instead of wf-engine for analysis chains
3. Pass recon data directly in the prompt string rather than via agent() return values
4. Keep individual prompts under ~1500 chars when using wf-engine multi-agent workflows

## Full Autonomy Preference

When user says "全权交给你负责" (full authority), this means:
- Agent should independently choose next exploitation steps
- Report findings continuously, don't wait for instructions for every step
- Present final findings with clear severity ratings
- Don't ask "what to do next" — just do it and report results
