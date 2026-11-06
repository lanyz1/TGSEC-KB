## Standard Claude Code

| File | Path | Purpose |
|------|------|---------|
| Base config | `~/.claude/config.toml` | `model_instructions_file = "..."` |
| User settings | `~/.claude/settings.json` | Permissions, MCP servers |
| State/UX | `~/.claude.json` | Growthbook features, projects, auth |
| Credentials | `~/.claude/.credentials.json` | OAuth tokens (Claude AI account) |
| System prompt | `~/.claude/system-prompt.md` | Identity/personality instructions |
| Project CLAUDE.md | `<project-root>/CLAUDE.md` | Per-project agent instructions |

Standard Claude Code's **model provider** comes from the API key in credentials 
— it always hits Anthropic's official API.

---

