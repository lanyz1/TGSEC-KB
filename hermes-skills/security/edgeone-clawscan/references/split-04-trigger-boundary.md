## Trigger Boundary

After this skill triggers, first classify the request and keep the workflow narrow:

- Run **Feature 1: OpenClaw Security Scan** when the user explicitly asks to start a security health check or security scan for the current OpenClaw environment, including phrasing such as `开始安全体检`, `做一次安全体检`, `开始安全扫描`, `做一次全面安全检查`, or `给 OpenClaw 做安全体检`.
- Run **Feature 2: Skill Security Scan** when the user asks whether a specific skill is safe, wants a pre-install security check, or needs to audit one or more installed skills.

Do not treat ordinary mentions of `openclaw`, `clawdbot`, dependency installation, project debugging, or normal development tasks as a reason to run this skill.

---

