## Hermes Agent (custom provider)

Hermes Agent stores its own provider config in the active profile's `config.yaml` (Windows: `~/AppData/Local/hermes/profiles/<profile>/config.yaml`):

```yaml
model:
  default: deepseek-v4-pro        # model id exactly as the relay exposes it
  provider: custom                # 'custom' = use base_url + api_key below
  base_url: https://relay.example.com   # may need /v1 — verify first
  api_key: sk-...
```

Workflow (verify BEFORE writing config):
1. Probe the endpoint exactly as you will configure it:
   ```bash
   curl -s https://relay.example.com/v1/models -H "Authorization: Bearer sk-..."
   # {"data":[{"id":"deepseek-v4-pro",...}]} → good; if 404 try without /v1
   ```
2. Apply via CLI, never hand-edit config.yaml (a stray indent breaks the live gateway):
   ```bash
   hermes config set model.provider custom
   hermes config set model.base_url https://relay.example.com/v1
   hermes config set model.api_key sk-...
   hermes config set model.default deepseek-v4-pro
   ```
3. Confirm with `hermes model` / `hermes doctor`.

Pitfall: relays in China often serve `/models` on BOTH `/v1/models` and `/models`; test the exact path you configure. `/v1/models` 200 does NOT guarantee chat completions work — run one real request to confirm.

### Profile API key troubleshooting ("api 不能正常调用")

Fast diagnosis path for a Hermes profile whose API calls fail (verified Aug 2026, deepseek):

1. **Read the credential pool state** — `<profile>/auth.json` holds the last auth result per provider:
   ```python
   import json
   d = json.load(open(r'C:\Users\<user>\AppData\Local\hermes\profiles\<profile>\auth.json', encoding='utf-8'))
   for c in d['credential_pool'].get('deepseek', []):
       print(c.get('last_status'), c.get('last_error_code'), c.get('last_error_message'))
   ```
   `last_status: exhausted` + `last_error_code: 401` + `Authentication Fails, Your api key: ****x is invalid` = the key itself is dead at the provider (revoked/rotated/typo) — NOT a network or config problem.

2. **Probe the key directly** (don't trust the pool status alone):
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://api.deepseek.com/v1/models -H "Authorization: Bearer $KEY"
   # 200 = key fine; 401 = key invalid. Compare against a known-good profile's key for contrast.
   ```

3. **Fix recipe**:
   - Replace the key in `<profile>/.env` (line `DEEPSEEK_API_KEY=...`). Use Python `io.open(..., newline='')` and write the line with `\r\n` to preserve the file's CRLF — a plain write_file can mangle line endings.
   - Clear the exhausted flag, or the pool keeps skipping the key even after it's fixed:
     ```bash
     HERMES_HOME='C:\Users\<user>\AppData\Local\hermes\profiles\<profile>' hermes auth reset deepseek
     ```
   - Verify: auth.json `last_status` back to `None` and curl returns 200.
   - **Restart the profile's session/window** — running sessions cache the old key + exhausted state.

### Pitfalls (Hermes profiles)

- **`HERMES_PROFILE=<name> hermes ...` does NOT scope CLI commands to that profile** — it silently runs against the sticky default profile (set via `hermes profile use`). Symptom: `hermes auth reset` says "Reset status on 1 credentials" but the WRONG profile's auth.json changed. Scope with `HERMES_HOME='C:\...\profiles\<name>'` instead; confirm which profile was touched by checking auth.json `updated_at`.
- **Repeated 401s freeze the key**: the credential pool marks a key `exhausted` after auth failures and stops trying it. Fixing `.env` alone is NOT enough — run `hermes auth reset <provider>` (scoped to the right profile).
- **DeepSeek 401 message** "Authentication Fails, Your api key: ****x is invalid" = key invalid (balance errors are 402, not 401). A well-formed 35-char `sk-...` key can still be dead platform-side.
- **Profile dirs on this Windows setup**: `C:\Users\<user>\AppData\Local\hermes\profiles\<name>\` (NOT `~/.hermes/profiles`); the active session's HERMES_HOME points at its own profile dir.
- **Hermes redacts keys in tool output** (`grep` shows `sk-f3e...c34c` even though the file holds the full key) — to read/replace a key programmatically use Python, not grep/read_file.

