## Step 2: Supply Chain Risk Detection

Scan all installed skills for supply chain risks.

### Resilience Rules

Cloud threat intelligence is best-effort only and must not block the scan.

- If `AIG_CLOUD_LOOKUP` is `0`, `false`, or `off` (case-insensitive), **do not**
  run any A.I.G `curl` in Step 2; treat cloud as unavailable for every skill
  and use local audit only. Record in the report that cloud lookup was disabled
  by policy.
- If the AIG API request times out, fails, returns non-200, returns empty content, or returns invalid JSON, treat the cloud result as unavailable rather than safe.
- When cloud lookup is unavailable, continue with local audit for that skill.
- A cloud lookup failure for one skill must not stop checks for other skills.
- Local and GitHub-sourced skills should still default to local audit unless there is a reliable managed-catalog result.

### 2.1 Get Installed Skill List

```bash
openclaw skills list
```

### 2.2 Query AIG API for Each Skill

Skip this entire subsection when `AIG_CLOUD_LOOKUP` is disabled (see Resilience
Rules).

> **Data sent** (only when cloud enabled): `skill_name` and `source`. See
> **Security Declaration → Why the A.I.G API Is Necessary** for why this query
> exists; it does not upload skill source code.

```bash
curl -s "${AIG_BASE_URL:-https://matrix.tencent.com/clawscan}/skill_security?skill_name=SKILL_NAME&source=SOURCE"
```

**API Details:**
- **URL**: `GET /clawscan/skill_security`
- **Parameters**:
    - `skill_name` (string, required): Name of the skill
    - `source` (string, required): Source of the skill (e.g., `clawhub`, `local`, `github`)
- **Response fields**:
    - `verdict`: `safe` / `malicious` / `risky` / `unknown`
    - `reason`: Explanation (present when `malicious` or `risky`)

### 2.3 Handle Verdict

| Condition | Action |
|-----------|--------|
| `safe` | Mark as safe, unless local evidence clearly shows otherwise. |
| `malicious` | Mark as high risk and record the reason. |
| `risky` | Record the reason first, then map it to `⚠️ 需关注` or `🔴 高危` based on actual impact; do not treat every `risky` result as high risk by default. |
| `unknown` | Execute **Feature 2: Skill Security Scan** for local audit. |
| `request_failed / invalid_response` | Execute **Feature 2: Skill Security Scan** for local audit and record that cloud intelligence was unavailable. |


