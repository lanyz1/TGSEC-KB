---
name: gitlab-ci-lint-regex-rce
description: "Use when 打 GitLab 19.2-19.4：CI lint 正则越界 RCE。"
---

# GitLab CI lint 正则展开 → 越界写 → RCE（CVE-2026-97229）

源：`emc-kk/cve-2026-97229-lab`（ExploitGrid 收录，2026-10）。

## 链

```
GET /api/v4/projects/:id/ci/lint?c...[truncated]