## Codex CLI (on Windows)

| File | Path | What it holds |
|------|------|---------------|
| Config | `~/.codex/config.toml` | `model`, `model_provider`, `base_url`, `wire_api` |
| Agent protocol | `~/.codex/AGENTS.md` | Per-project agent instructions |
| Sessions | `~/.codex/sessions/` | JSONL session history |

### Codex custom provider config

```toml
model_provider = "custom"

[model_providers.custom]
name = "My Provider"
base_url = "https://api.example.com/v1"
wire_api = "responses"           # Can be "responses" or "chat"
requires_openai_auth = true
experimental_bearer_token = "sk-..."
```

`wire_api = "responses"` means the proxy mimics OpenAI's `responses` API.
`wire_api = "chat"` means it mimics the Chat Completions API.

---

