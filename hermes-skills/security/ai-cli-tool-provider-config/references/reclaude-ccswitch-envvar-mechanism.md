# ReClaude + CC-Switch Provider Discovery (2026-07-12)

## Context

User has both Claude Code (with ReClaude fork) and Codex installed on Windows.
CC-Switch manages provider switching. The question was: where is `model_provider`
configured in ReClaude?

## Finding

ReClaude does NOT use a text-file `model_provider` setting. Instead:

1. **CC-Switch DB** (`~/.cc-switch/cc-switch.db`) stores provider definitions
   in the `providers` table, each with a `settings_config` JSON column.
2. The **`settings` table** has `currentProviderClaude` and `currentProviderCodex`
   keys that point to the active provider ID.
3. CC-Switch **injects environment variables** into the ReClaude daemon process
   at startup — specifically `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`.
4. These env vars are NOT visible in a normal shell (`env` shows nothing) —
   they exist only inside the daemon process tree.

## CC-Switch DB Schema (providers table)

| Column | Type | Content |
|--------|------|---------|
| id | TEXT | e.g. `rightcode-1783706964495` |
| app_type | TEXT | `claude`, `codex`, `gemini` |
| name | TEXT | Human name: `Right Code`, `My Codex` |
| settings_config | TEXT | JSON blob with `env` or `auth`+`config` |
| provider_type | TEXT | `official` or null |
| is_current | INT | 0/1 |
| created_at | INT | Timestamp |

## Provider examples discovered

| ID | App | Name | Mechanism |
|----|-----|------|-----------|
| `rightcode-1783706964495` | claude | Right Code | env vars (`ANTHROPIC_*`) |
| `fkcodex-1783349864352` | claude | fkcodex | env vars + model overrides |
| `claude-official` | claude | Claude Official | empty env (uses built-in auth) |
| `mycodex-1783865031482` | codex | My Codex | custom provider section + bearer token |
| `codex-official` | codex | OpenAI Official | ChatGPT OAuth tokens |
| `default` | claude | default | empty, fallback |

## Right Code provider settings

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://www.right.codes/claude",
    "ANTHROPIC_AUTH_TOKEN": "sk-979...180e"
  }
}
```

## fkcodex provider settings (with model overrides)

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://www.fkcodex.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-QbQ...h9TR",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
    "ANTHROPIC_MODEL": "claude-fable-5"
  }
}
```

## ReClaude daemon state

```json
{
  "daemon": {
    "running": true,
    "pid": 108068,
    "port": 65295,
    "transparent_port": 65296,
    "version": "v1.2.4"
  },
  "gateway": {
    "url": "https://www.reclaude.ai",
    "healthy": true
  },
  "login_base_url": "https://www.recode.cat"
}
```

## ReClaude device/auth

```json
{
  "sk": "sk-...",
  "device_id": 35762,
  "gateway_url": "https://www.reclaude.ai",
  "user_email": "<EMAIL-REDACTED>"
}
```
