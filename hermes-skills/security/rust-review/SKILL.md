---
name: rust-review
description: >-
 测绘引擎·Performs comprehensive Rust security review for safe/unsafe boundary issues, memory
 safety in unsafe blocks, concurrency hazards, panic-induced DoS, FFI safety, and async
 runtime mistakes. Use when auditing Rust crates, services, or libraries — particularly
 those with `unsafe`, FFI, or concurrent code.
owned: true
pack: survey-skill
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='rust-review', file_path='references/full.md')`

# rust-review（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/rust-review/`

溯源（仅标记）：`trailofbits/skills`

---

# Rust Security Review

Orchestrator skill (invoke via `/rust-review:rust-review`). Workers and judges are plugin subagents. Findings exchanged via markdown-with-YAML files in a shared output directory.

<!-- split-index -->

## Section index

- [When to Use](references/split-01-when-to-use.md)
- [When NOT to Use](references/split-02-when-not-to-use.md)
- [Subagents](references/split-03-subagents.md)
- [Architecture](references/split-04-architecture.md)
- [Orchestration Phases](references/split-05-orchestration-phases.md)
- [Finding Frontmatter Stages](references/split-06-finding-frontmatter-stages.md)
- [Bug Classes](references/split-07-bug-classes.md)
- [Success Criteria](references/split-08-success-criteria.md)
- [真源](references/split-09-section.md)
- [外部库增量（2026-10-11 分享包）](references/split-10-2026-10-11.md)
- [Rationalizations to Reject](references/split-11-rationalizations-to-reject.md)
- [Orchestration Workflow](references/split-12-orchestration-workflow.md)
- [Finding file frontmatter — three stages](references/split-13-finding-file-frontmatter-three-stages.md)
- [Bug classes / clusters](references/split-14-bug-classes-clusters.md)
