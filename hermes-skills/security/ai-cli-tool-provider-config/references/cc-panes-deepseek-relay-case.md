# CC-Panes + DeepSeek via fkcodex relay — probe transcript (Aug 2026)

Goal: run `deepseek-v4-flash` inside CC-Panes using the user's fkcodex relay (not official key).
Result: **blocked at the relay** — fkcodex serves `/v1/chat/completions` but NOT
`/v1/responses` (which CC-Panes' Codex adapter hardcodes) and has NO Claude channel for
deepseek (so the `claude` target is out too).

## Relay capability probe (fkcodex, new-api family)

| Endpoint | Result | Meaning |
|---|---|---|
| `GET /v1/models` (Bearer relay token) | HTTP 200 | lists: `deepseek-v4-flash`, `deepseek-v4-pro`, `glm-5.2`, `kimi-k3`, `minimax-m3` |
| `POST /v1/chat/completions` model=deepseek-v4-flash | HTTP 200 | `{"object":"chat.completion", ... "content":"pong"}` |
| `POST /v1/responses` model=deepseek-v4-flash | HTTP 500 (×3) | `{"error":{"message":"The service encountered a temporary issue. Please retry later.","type":"server_error"}}` — dead end |
| `POST /v1/responses` model=glm-5.2 | HTTP 200 (2nd attempt, 29s; 1st attempt HTTP 000 timeout) | relay's responses endpoint works for SOME models, 500s for deepseek |
| `POST /v1/messages` (Anthropic proto) model=deepseek-v4-flash | HTTP 503 | `{"error":{"code":"model_not_found","message":"No available channel for model deepseek-v4-flash under group 国模分组 (distributor)","type":"new_api_error"}}` |

Keys findings:
- fkcodex uses new-api (`"type":"new_api_error"`); deepseek models sit in "国模分组" (domestic
  model group) which has NO Anthropic-protocol channel → `claude` target can never work for
  deepseek on this relay.
- `/v1/responses` is flaky for deepseek (500) but works for glm-5.2 → a new-api relay admin
  could likely enable it; it's not fundamentally absent. First attempt can also be HTTP 000
  (timeout) — retry once before concluding dead.
- Official DeepSeek API (`https://api.deepseek.com/v1`) DOES return 200 on `/v1/responses`
  with a proper `{"object":"response", ...}` body → official-key users can use Codex target.

## CC-Panes source facts (D:\cc-pane, Aug 2026)

- `cc-panes-core/src/models/provider.rs` — `ProviderType` enum + `to_env_vars()`:
  `open_ai` → `CODEX_API_KEY` + `OPENAI_BASE_URL`; `proxy` → `ANTHROPIC_API_KEY` +
  `ANTHROPIC_BASE_URL`; `opencode` → `OPENAI_API_KEY` + `OPENAI_BASE_URL`.
- `cc-cli-adapters/src/codex.rs` — `CodexAdapter::new()` caps `compatible_provider_types =
  ["open_ai", "config_profile"]`; `push_provider_overrides()` writes `-c
  model_providers.<key>.wire_api=responses` (hardcoded), `-c model_provider=<key>`, base_url,
  and `env_key=CCPANES_CODEX_API_KEY` (key passed via env, not argv). Also `-c
  model_reasoning_effort=<v>` from adapter_options.effort, and `extra_args_from_options`
  appends `adapter_options.extraArgs` array AFTER the provider overrides.
- Modern Codex CLI (Jul 2026 build) rejects `wire_api="chat"` outright:
  `Error loading config.toml: wire_api = "chat" is no longer supported. How to fix: set
  wire_api = "responses"` → no chat-completions fallback exists anymore.
- Launch Profile / Provider carry NO model field — model lives in `~/.codex/config.toml`
  top-level `model = "..."` (user's was `gpt-5.5` for fkcodex).
- `cc-panes-web` exposes the API on `http://127.0.0.1:18080/` (release): `/api/providers`,
  `/api/launch-profiles`, `/api/launch-profiles/preview` — GUI-less verification path.

## Why "won't open" fooled us mid-task

While probing, a fresh `cc-panes.exe` launch exited after 15s with boot log stopping at
`building tauri app...` — looked like a startup crash. Actual cause: the app was ALREADY
running (old instance, single-instance lock), and the new instance exits after handing off.
Check `tasklist | grep -i cc-panes` BEFORE concluding the app is down. See
`windows-app-crash-troubleshooting` → "hidden window" recovery for the full fix.

## Options if user insists on deepseek-v4-flash inside CC-Panes

1. Relay-side: ask fkcodex admin to enable `/v1/responses` for deepseek (glm works, so likely
   fixable) — then Codex target works with providerType `open_ai`, baseUrl fkcodex, model set
   in `~/.codex/config.toml`.
2. Patch `codex.rs` `push_provider_overrides` to read wire_api from adapter_options (or drop
   the hardcode) and rebuild — but modern Codex CLI rejects chat, so this only helps if the
   relay gains responses support anyway.
3. Use a different relay that already proxies deepseek through `/v1/responses`.
4. Claude target: only if relay adds deepseek to an Anthropic-compatible channel group.
