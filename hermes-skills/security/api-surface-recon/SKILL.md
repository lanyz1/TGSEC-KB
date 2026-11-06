---
name: api-surface-recon
description: "Use when mapping a hardened API before attacking it."
version: 1.1.0
tags: [recon, api, spa, traversal, ssrf, gin, fastapi, bfla, user-enumeration]
---

# API Surface Recon (hardened / undocumented)

Use when you have a live backend, no docs, and the front door is a SPA. Goal: turn the frontend bundle into a
complete API + auth map, and know which of your conclusions are actually trustworthy.

<!-- split-index -->

## Section index

- [Procedure](references/split-01-procedure.md)
- [Pitfalls](references/split-02-pitfalls.md)
