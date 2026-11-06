---
name: claude-code
description: "Delegate coding to Claude Code CLI (features, PRs)."
version: 2.2.1
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Claude, Anthropic, Code-Review, Refactoring, PTY, Automation]
    related_skills: [codex, hermes-agent, opencode]
---

# Claude Code — Hermes Orchestration Guide

Delegate coding tasks to [Claude Code](https://code.claude.com/docs/en/cli-reference) (Anthropic's autonomous coding agent CLI) via the Hermes terminal. Claude Code v2.x can read files, write code, run shell commands, spawn subagents, and manage git workflows autonomously.

<!-- split-index -->

## Section index

- [Prerequisites](references/split-01-prerequisites.md)
- [Two Orchestration Modes](references/split-02-two-orchestration-modes.md)
- [PTY Dialog Handling (CRITICAL for Interactive Mode)](references/split-03-pty-dialog-handling-critical-for-interac.md)
- [CLI Subcommands](references/split-04-cli-subcommands.md)
- [Print Mode Deep Dive](references/split-05-print-mode-deep-dive.md)
- [Complete CLI Flags Reference](references/split-06-complete-cli-flags-reference.md)
- [Settings & Configuration](references/split-07-settings-configuration.md)
- [Interactive Session: Slash Commands](references/split-08-interactive-session-slash-commands.md)
- [Interactive Session: Keyboard Shortcuts](references/split-09-interactive-session-keyboard-shortcuts.md)
- [PR Review Pattern](references/split-10-pr-review-pattern.md)
- [Parallel Claude Instances](references/split-11-parallel-claude-instances.md)
- [CLAUDE.md — Project Context File](references/split-12-claude-md-project-context-file.md)
- [Custom Subagents](references/split-13-custom-subagents.md)
- [Hooks — Automation on Events](references/split-14-hooks-automation-on-events.md)
- [MCP Integration](references/split-15-mcp-integration.md)
- [Monitoring Interactive Sessions](references/split-16-monitoring-interactive-sessions.md)
- [Environment Variables](references/split-17-environment-variables.md)
- [Cost & Performance Tips](references/split-18-cost-performance-tips.md)
- [Pitfalls & Gotchas](references/split-19-pitfalls-gotchas.md)
- [Rules for Hermes Agents](references/split-20-rules-for-hermes-agents.md)
