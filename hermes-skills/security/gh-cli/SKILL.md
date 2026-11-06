---
name: gh-cli
description: >-
 测绘引擎·Enforces authenticated gh CLI workflows over unauthenticated curl/WebFetch
 patterns. Use when working with GitHub URLs, API access, pull requests, or issues.
owned: true
pack: survey-skill
---

# gh-cli（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/gh-cli/`

溯源（仅标记）：`trailofbits/skills`

---

# gh-cli

## When to Use

- Working with GitHub repositories, pull requests, issues, releases, or raw file URLs.
- You need authenticated access to private repositories or higher API rate limits.
- You are about to use `curl`, `wget`, or unauthenticated web fetches against GitHub.

## When NOT to Use

- The target is not GitHub.
- Plain local git operations already solve the task.

## Guidance

Prefer the authenticated `gh` CLI over raw HTTP fetches for GitHub content. In particular:

- Prefer `gh repo view`, `gh pr view`, `gh pr list`, `gh issue view`, and `gh api` over unauthenticated `curl` or `wget`.
- Prefer cloning a repository and reading files locally over fetching `raw.githubusercontent.com` blobs directly.
- Avoid using GitHub API `/contents/` endpoints as a substitute for cloning and reading repository files.

Examples:

```sh
gh repo view owner/repo
gh pr view 123 --repo owner/repo
gh api repos/owner/repo/pulls
```

For the hook implementation, see:
- `plugins/gh-cli/README.md`
- `plugins/gh-cli/hooks/`

## 真源

- 工具：`python3 tools/ops/case_report.py --help`
