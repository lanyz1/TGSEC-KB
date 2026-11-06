---
name: research-paper-writing
title: Research Paper Writing Pipeline
description: "Write ML papers for NeurIPS/ICML/ICLR: design→submit."
version: 1.1.0
author: Orchestra Research
license: MIT
dependencies: [semanticscholar, arxiv, habanero, requests, scipy, numpy, matplotlib, SciencePlots]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Research, Paper Writing, Experiments, ML, AI, NeurIPS, ICML, ICLR, ACL, AAAI, COLM, LaTeX, Citations, Statistical Analysis]
    category: research
    related_skills: [arxiv, subagent-driven-development, plan]
    requires_toolsets: [terminal, files]

---

# Research Paper Writing Pipeline

End-to-end pipeline for producing publication-ready ML/AI research papers targeting **NeurIPS, ICML, ICLR, ACL, AAAI, and COLM**. This skill covers the full research lifecycle: experiment design, execution, monitoring, analysis, paper writing, review, revision, and submission.

This is **not a linear pipeline** — it is an iterative loop. Results trigger new experiments. Reviews trigger new analysis. The agent must handle these feedback loops.

<!-- ascii-guard-ignore -->
```
┌─────────────────────────────────────────────────────────────┐
│                    RESEARCH PAPER PIPELINE                  │
│                                                             │
│  Phase 0: Project Setup ──► Phase 1: Literature Review      │
│       │                          │                          │
│       ▼                          ▼                          │
│  Phase 2: Experiment     Phase 5: Paper Drafting ◄──┐      │
│       Design                     │                   │      │
│       │                          ▼                   │      │
│       ▼                    Phase 6: Self-Review      │      │
│  Phase 3: Execution &           & Revision ──────────┘      │
│       Monitoring                 │                          │
│       │                          ▼                          │
│       ▼                    Phase 7: Submission               │
│  Phase 4: Analysis ─────► (feeds back to Phase 2 or 5)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
<!-- ascii-guard-ignore-end -->

---

<!-- split-index -->

## Section index

- [When To Use This Skill](references/split-01-when-to-use-this-skill.md)
- [Core Philosophy](references/split-02-core-philosophy.md)
- [Phase 0: Project Setup](references/split-03-phase-0-project-setup.md)
- [Phase 1: Literature Review](references/split-04-phase-1-literature-review.md)
- [Phase 2: Experiment Design](references/split-05-phase-2-experiment-design.md)
- [Phase 3: Experiment Execution & Monitoring](references/split-06-phase-3-experiment-execution-monitoring.md)
- [Phase 4: Result Analysis](references/split-07-phase-4-result-analysis.md)
- [Iterative Refinement: Strategy Selection](references/split-08-iterative-refinement-strategy-selection.md)
- [Phase 5: Paper Drafting](references/split-09-phase-5-paper-drafting.md)
- [Phase 6: Self-Review & Revision](references/split-10-phase-6-self-review-revision.md)
- [Phase 7: Submission Preparation](references/split-11-phase-7-submission-preparation.md)
- [Phase 8: Post-Acceptance Deliverables](references/split-12-phase-8-post-acceptance-deliverables.md)
- [Workshop & Short Papers](references/split-13-workshop-short-papers.md)
- [Paper Types Beyond Empirical ML](references/split-14-paper-types-beyond-empirical-ml.md)
- [Hermes Agent Integration](references/split-15-hermes-agent-integration.md)
- [Reviewer Evaluation Criteria](references/split-16-reviewer-evaluation-criteria.md)
- [Common Issues and Solutions](references/split-17-common-issues-and-solutions.md)
- [Reference Documents](references/split-18-reference-documents.md)
