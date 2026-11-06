## Quick Reference: Where is model_provider?

| Tool | Config location | Provider mechanism |
|------|----------------|-------------------|
| **Claude Code** (official) | `~/.claude/.credentials.json` | OAuth → Anthropic API |
| **ReClaude** | `~/.cc-switch/cc-switch.db` | CC-Switch env vars → daemon proxy |
| **Codex** (official) | `~/.codex/config.toml` | `model_provider` + OAuth to OpenAI |
| **Codex** (custom) | `~/.codex/config.toml` | `model_providers.custom` section |
| **Hermes Agent** | `~/AppData/Local/hermes/profiles/<profile>/config.yaml` | `model.base_url` + `model.api_key` (provider: custom) |

