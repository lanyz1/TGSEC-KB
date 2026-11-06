---
name: codex
description: "Delegate coding to OpenAI Codex CLI (features, PRs)."
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
    related_skills: [claude-code, hermes-agent]
---

# Codex CLI

Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.

## When to use

- Building features
- Refactoring
- PR reviews
- Batch issue fixing

Requires the codex CLI and a git repository.

## Prerequisites

- Codex installed: `npm install -g @openai/codex`
- OpenAI auth configured: either `OPENAI_API_KEY` or Codex OAuth credentials
  from the Codex CLI login flow
- **Must run inside a git repository** — Codex refuses to run outside one
- Use `pty=true` in terminal calls — Codex is an interactive terminal app

For Hermes itself, `model.provider: openai-codex` uses Hermes-managed Codex
OAuth from `~/.hermes/auth.json` after `hermes auth add openai-codex`. For the
standalone Codex CLI, a valid CLI OAuth session may live under
`~/.codex/auth.json`; do not treat a missing `OPENAI_API_KEY` alone as proof
that Codex auth is missing.

## One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

## Background Mode (Long Tasks)

```
# Start in background with PTY
terminal(command="codex exec --sandbox workspace-write 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--sandbox workspace-write` (`-s`) | Sandboxed but auto-approves file changes in the workspace (the recommended auto-build mode) |
| `--dangerously-bypass-approvals-and-sandbox` | No sandbox, no approvals (fastest, most dangerous; `--yolo` still works as a hidden alias) |
| `--sandbox danger-full-access` | No Codex sandbox; useful when the host service context breaks bubblewrap |

> **Deprecated:** `--full-auto` still works but the live CLI warns to use `--sandbox workspace-write` instead.

## Hermes Gateway Caveat

When invoking the Codex CLI from a Hermes gateway/service context (for example,
Telegram-driven agent sessions), Codex `workspace-write` sandboxing may fail even
when the same command works in the user's interactive shell. A typical symptom is
bubblewrap/user-namespace errors such as `setting up uid map: Permission denied`
or `loopback: Failed RTM_NEWADDR: Operation not permitted`.

In that context, prefer:

```
codex exec --sandbox danger-full-access "<task>"
```

Use process boundaries as the safety layer instead: explicit `workdir`, clean git
status before launch, narrow task prompts, `git diff` review, targeted tests, and
human/agent confirmation before committing broad changes.

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex --sandbox workspace-write exec 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="codex --sandbox workspace-write exec 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Rules

1. **Always use `pty=true`** — Codex is an interactive terminal app and hangs without a PTY
2. **Git repo required** — Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch
3. **Use `exec` for one-shots** — `codex exec "prompt"` runs and exits cleanly
4. **`--sandbox workspace-write` for building** — auto-approves changes within the sandbox (`--full-auto` is deprecated for this)
5. **Background for long tasks** — use `background=true` and monitor with `process` tool
6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks
7. **Parallel is fine** — run multiple Codex processes at once for batch work


---

## 外部库增量（2026-10-11 分享包）

## Third-Party Providers (DeepSeek, relays) — Codex 0.154+ verified

Config lives at `~/.codex/config.toml` (`%USERPROFILE%\.codex\config.toml` on Windows).
A provider is a table plus two top-level keys:

```toml
model_provider = "deepseek"
model = "deepseek-flash"

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com/v1"
wire_api = "responses"
requires_openai_auth = false
experimental_bearer_token = "sk-..."   # or env_key = "DEEPSEEK_API_KEY"
```

Hard rules learned the hard way on 0.154.0-alpha:

1. **`wire_api = "chat"` is gone.** Codex refuses to start: `wire_api = "chat" is no longer supported / set wire_api = "responses"`.
   `openai_chat`-only upstreams therefore need a local translating proxy (cc-switch does this) or an upstream that speaks `/v1/responses`.
2. **`[profiles.<name>]` inside config.toml is legacy and now an error.** Profiles must be their own file: `~/.codex/<name>.config.toml`
   containing just overrides (e.g. `model` / `model_provider`); run with `codex --profile <name>`. A profile file does NOT inherit
   `model_providers` from config.toml — keep provider tables in config.toml and only override model names in the profile.
3. **Model metadata warning** (`Model metadata for X not found. Defaulting to fallback metadata`) is silenced by
describing the model: `model_context_window`, `model_max_output_tokens`, or a `model_catalog_json` catalogue file.
4. **A config manager may own config.toml.** On this user's box **cc-switch** (`D:\cc-switch.exe`, data in `~/.cc-switch/`, local
   proxy `127.0.0.1:15721`) rewrites `~/.codex/config.toml` wholesale on every provider switch — hand edits vanish within minutes
   and profiles then report `Model provider 'X' not found`. Either configure everything inside cc-switch, or exit it first.
5. **DeepSeek specifics (verified by live probe):** `GET https://api.deepseek.com/v1/models` -> `deepseek-flash`, `deepseek-v4-pro`;
   `POST /v1/responses` returns 200 with native `reasoning` output items, so no chat shim is needed. `service_tier` from an
   OpenAI-flavoured config is ignored with a harmless warning. Codex's system prompt makes the model self-identify as "Codex based on
   GPT-5" regardless of the real backend — that is not a misconfiguration.

Verify end-to-end (never trust the config alone):

```
codex exec --profile <name> --sandbox danger-full-access --skip-git-repo-check "run `echo OK` and report the output"
```

Success = banner shows `model: <yours>` / `provider: <yours>` and the model actually executes the shell tool.
On Windows the CLI binary lives at `%LOCALAPPDATA%\OpenAI\Codex\bin\<hash>\codex.exe` (see `CODEX_CLI_PATH` in config.toml);
`codex doctor` diagnoses config/auth/runtime health.
