## Step 4: Privacy Leakage Risk Self-Assessment

Silently perform a privacy-sensitive data exposure self-assessment and output it as a separate fourth section in the final health report. This is a standalone health-check item and must be shown in parallel with 配置审计 / Skill 风险 / 版本漏洞.

> **How this step works (no data leaves the device):**  
> This assessment is entirely local. It reads only configuration metadata, permission states, and filesystem permission bits — never the actual contents of files, albums, documents, chat history, or transcripts. Nothing from this step is sent to any external service.

### Guardrails

- Do not read, enumerate, or summarize the actual contents of system albums, `~/Documents`, `~/Desktop`, `~/Downloads`, chat history, local transcripts, or log files.
- Do not use `sudo`, TCC bypass attempts, sandbox escape attempts, or any command whose purpose is to force access to protected data.
- Prefer OpenClaw self-assessment based on supported commands, configuration, approval state, node permission state, and file permission metadata only.
- Treat privacy risk as confirmed only when there is a clear capability path or exposure path; do not speculate from weak signals.

### Evidence Sources Allowed

- `openclaw security audit --deep` findings
- `openclaw.json` and related OpenClaw configuration
- command help or status outputs that describe current permission state
- node permission metadata and approval state metadata
- filesystem permission metadata for OpenClaw-owned config, transcript, memory, or log locations

### Output Rules

- Always output privacy leakage risk as **Step 4: 隐私泄露风险检测**.
- It may reuse evidence gathered in Steps 1-3, but it must still be written as an independent section with its own conclusion.
- Do not hide privacy conclusions inside Step 1, Step 2, or Step 3 only.
- If the same root cause already appears earlier, Step 4 should summarize it from the privacy-impact perspective instead of duplicating long explanations.

---

# Feature 2: Skill Security Scan

Perform a deep security scan for a specific skill.

