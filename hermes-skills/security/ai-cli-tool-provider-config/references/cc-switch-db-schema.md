# CC-Switch SQLite DB — Full Schema & Patterns

DB: `~/.cc-switch/cc-switch.db` (SQLite). GUI app `D:\cc-switch.exe` on this machine, but **direct DB writes work** — GUI is a thin wrapper over the same DB. Read before write: dump the `providers` table to see the exact shapes currently in use.

## providers table — full column list

```sql
SELECT * FROM providers;
-- columns:
-- id, app_type, name, settings_config, website_url, category, created_at,
-- sort_index, notes, icon, icon_color, meta, is_current, in_failover_queue,
-- cost_multiplier, limit_daily_usd, limit_monthly_usd, provider_type
```

INSERT template that works (omit nullable columns):

```python
import sqlite3, json, time
conn = sqlite3.connect(r'C:\Users\Administrator\.cc-switch\cc-switch.db')
cur = conn.cursor()
cur.execute("""
    INSERT OR REPLACE INTO providers
    (id, app_type, name, settings_config, website_url, category, created_at,
     is_current, in_failover_queue, cost_multiplier)
    VALUES (?,?,?,?,?,?,?,?,?,?)
""", (
    f"relay-{int(time.time()*1000)}", "claude", "Name",
    json.dumps(settings), "https://relay.example", None,
    int(time.time()*1000), 1, 0, 1.0
))
conn.commit()
```

## settings_config shapes per app_type

**claude** — `env` block (ANTHROPIC_* env vars injected into the CLI/daemon):
```json
{"env": {
  "ANTHROPIC_AUTH_TOKEN": "sk-...",
  "ANTHROPIC_BASE_URL": "https://relay.example",
  "ANTHROPIC_MODEL": "claude-fable-5",
  "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
  "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
  "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001"
}}
```

**codex** — `auth` + full TOML `config` string:
```json
{"auth": {"OPENAI_API_KEY": "sk-..."},
 "config": "model_provider = \"custom\"\nmodel = \"gpt-5.5\"\n[model_providers.custom]\nname = \"relay\"\nbase_url = \"https://relay.example/v1\"\nwire_api = \"responses\"\nrequires_openai_auth = true\nexperimental_bearer_token = \"sk-...\"\n"}
```

## meta.usage_script — embedded balance-query pattern

Relay providers (fkcodex, right.codes, etc.) carry a JS balance-query script inside `meta.usage_script` so CC Switch can show remaining quota in the GUI:

```json
{"usage_script": {"enabled": true, "language": "javascript",
  "code": "({request: {url: '{{baseUrl}}/api/usage/balance', method: 'GET',
    headers: {Authorization: 'Bearer {{apiKey}}'}},
    extractor: function (response) { /* parse balance, return {remaining, unit, isValid} */ }})",
  "timeout": 10, "baseUrl": "https://relay.example", "autoQueryInterval": 30}}
```

When adding a new relay, copy the usage_script shape from an existing fkcodex entry and change baseUrl + URL path. Bare IP relays (no dashboard) have no working balance endpoint — set `enabled: false` or omit.

## Switching / clearing providers

```python
# set one provider as current for an app_type
cur.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'codex'")
cur.execute("UPDATE providers SET is_current = 1 WHERE id = ?", (new_id,))
# order matters: zero-out first, then set
```

Clearing a whole app's config = zero all `is_current`, then let the target tool fall back to official or a fresh provider.

## Codex clean-slate config.toml (keep these sections)

When rewriting `~/.codex/config.toml` from scratch (e.g. clearing a jailbreak/pentest project's modifications), keep ONLY:

- `model_provider`, `model`, `model_reasoning_effort`, `disable_response_storage`
- `[model_providers.custom]` (the active relay)
- `[mcp_servers]` + `[mcp_servers.node_repl]` + its `.env` block (node_repl is Codex's built-in JS REPL — deleting it breaks the desktop app)
- `[desktop]`, `[marketplaces.openai-bundled]`, `[marketplaces.openai-primary-runtime]`, `[plugins.*]`, `[features]`, `[windows]`

Delete: `model_instructions_file` (jailbreak prompt pointer), `[projects.*]` trust entries, any `[mcp_servers.*]` blocks from third-party projects (e.g. reverse_lab_tools, burpsuite) unless the user still uses them, `[tui.*]` NUX counters.

## Pitfalls

- `settings_config.auth.OPENAI_API_KEY` values written by the app may appear redacted (`«redacted:sk-…»`) in the DB — plaintext INSERTs still work and are what the CLI actually reads.
- `is_current` must be updated even when `settings` table's `currentProviderClaude`/`currentProviderCodex` keys are also present — the daemon/GUI reads both. Check both after a switch.
- `proxy_config` table (`proxy_enabled`, `listen_port`) is a SEPARATE MITM-proxy mechanism from provider switching — disabling the proxy does not stop a relay provider.
