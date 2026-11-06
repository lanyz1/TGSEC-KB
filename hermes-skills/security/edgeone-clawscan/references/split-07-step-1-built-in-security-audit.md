## Step 1: Built-in Security Audit

Run the OpenClaw built-in security audit command:

```bash
openclaw security audit --deep
```

This command flags common security footguns such as:
- Gateway auth and network exposure
- Tool blast radius and risky open-room access
- Browser control or remote execution exposure
- Filesystem permissions and security misconfiguration

When run with `--deep`, it also attempts a best-effort live Gateway probe.

Interpret all built-in audit findings in this step as **configuration risk hints** only.  
Do not directly map any single built-in finding to `🔴 高危`; treat them as risk points that deserve attention and optimization, rather than evidence of an ongoing severe attack.

When writing **Step 1: 配置审计**, analyze only:
- findings emitted by `openclaw security audit --deep`

Do not mix in:
- Skill supply chain findings that belong in Step 2
- Local skill code audit results that belong in Step 2
- CVE or GHSA version advisories that belong in Step 3
- Privacy self-assessment conclusions that belong in Step 4

When summarizing Step 1 in the final report:
- Use plain language that focuses on "there is a risk" and "how to narrow it down", and avoid labels like "high risk" or "critical vulnerability" that may be misunderstood as confirmed severe incidents.
- Even when a configuration looks concerning, prefer wording such as "the current configuration has X risk, it is recommended to adjust Y" so that the emphasis stays on what is risky and how to become safer, instead of assigning scary severity labels.

