## CC-Panes + non-Anthropic models (DeepSeek etc. via relay) — probe BEFORE configuring

CC-Panes Provider `providerType` enum (cc-panes-core/src/models/provider.rs): `anthropic`,
`bedrock`, `vertex`, `proxy`, `config_profile`, `open_ai`, `gemini`, `kimi`, `glm`, `cursor`,
`opencode`, `grok`. Env injection (`Provider::to_env_vars`): `open_ai` → `CODEX_API_KEY` +
`OPENAI_BASE_URL`; `proxy`/`anthropic` → `ANTHROPIC_API_KEY` + `ANTHROPIC_BASE_URL`.

To run a non-Anthropic OpenAI-compatible model (e.g. `deepseek-v4-flash`) inside CC-Panes the
practical target is the **Codex CLI** adapter (cc-cli-adapters/src/codex.rs):
- `compatible_provider_types = ["open_ai", "config_profile"]` — pick `open_ai`.
- Launch Profile has **no model field**; Provider has **no model field**. The model name comes
  from the launched CLI's own config (`~/.codex/config.toml` top-level `model = "..."`).
- **Codex adapter hardcodes `wire_api="responses"`** (`push_provider_overrides` pushes
  `-c model_providers.<key>.wire_api=responses`). Modern Codex CLI **rejects
  `wire_api="chat"` outright** ("no longer supported ... set wire_api = responses"), so you
  cannot fall back to chat completions — the relay MUST serve `/v1/responses` for Codex to work.
- `adapter_options.extraArgs` (array) is appended to the codex argv — the only per-profile escape
  hatch, and it lands AFTER the provider overrides.

**Verify the relay's 4 endpoints before promising anything** (keys from `~/.cc-panes/providers.json`
or the user's relay panel):
```bash
curl -s "$BASE/v1/models"           -H "Authorization: Bearer $KEY"            # list models
curl -s "$BASE/v1/chat/completions"  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"ping"}],"max_tokens":20}'  # 200 = OK
curl -s "$BASE/v1/responses"        -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","input":"hi","max_output_tokens":5}'        # needed by Codex; 500 = dead end
curl -s "$BASE/v1/messages"         -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" -d '{"model":"deepseek-v4-flash","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'  # needed by claude target
```
Real-world result (Aug 2026, fkcodex new-api relay): `/v1/models` ✅ lists
deepseek-v4-flash/deepseek-v4-pro, `/v1/chat/completions` ✅ 200, `/v1/responses` ❌ 500
server_error, `/v1/messages` ❌ 503 model_not_found ("no available channel ... under group
国模分组" — deepseek has no Claude channel on that relay). **Conclusion: with this relay,
Codex/Claude targets both block; official `api.deepseek.com` does serve `/v1/responses` (200),
so official-key users are fine.** Relay options: wait for relay to enable responses / ask relay
admin, or patch codex.rs (`push_provider_overrides` wire_api line) and rebuild. Full probe
transcript: `references/cc-panes-deepseek-relay-case.md`.

