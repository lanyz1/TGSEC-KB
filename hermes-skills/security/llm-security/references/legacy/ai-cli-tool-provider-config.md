<!-- archived from /root/.hermes/skills/security/ai-cli-tool-provider-config/SKILL.md on 2026-10-21 -->

---
name: ai-cli-tool-provider-config
description: >-
  测绘引擎·Locate and understand model/provider configuration across Claude Code, ReClaude,
  Codex, and CC-Switch on Windows. Covers config file locations, the ReClaude daemon
  architecture, CC-Switch provider switching, and env-var injection mechanism. --- # AI
  CLI Tool Provider Configuration (Windows) ## Overview Many users run multiple AI coding
  CLIs (Claude Code, ReClaude fork, Codex) alongside **CC-Switch** for provider
  management. On Windows, config locations and the provide…
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/ai-cli-tool-provider-config`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ai-cli-tool-provider-config/…')`，不要相对 `references/legacy/` 解析。

# ai-cli-tool-provider-config（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ai-cli-tool-provider-config/`

溯源（仅标记）：`hermes/autonomous-ai-agents`

---

# AI CLI Tool Provider Configuration (Windows)

## Overview

Many users run multiple AI coding CLIs (Claude Code, ReClaude fork, Codex) 
alongside **CC-Switch** for provider management. On Windows, config locations 
and the provider mechanism differ from Linux/macOS.

---

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

## ReClaude (forked Claude Code)

ReClaude replaces the standard Claude Code with a **daemon-based proxy**:

```
rec.exe → daemon (127.0.0.1:port) → CC-Switch → provider endpoint
```

### Key files

| File | Path | What it holds |
|------|------|---------------|
| Daemon state | `~/.reclaude/state.json` | `daemon.port`, `daemon.transparent_port`, `gateway.url` |
| Device/auth | `~/.reclaude/device.json` | `sk` (secret key), `device_id`, `gateway_url` |
| Alias | `~/.reclaude/setup-aliases.json` | Shell alias pointing to `rec.exe` |
| App bundle | `~/.reclaude/claude-app/` | Full Electron GUI app (Claude Desktop fork) |

### How model_provider works in ReClaude

**It is NOT in a text config file.** ReClaude gets its provider configuration 
through **CC-Switch**, which injects environment variables into the daemon 
process:

```
ANTHROPIC_BASE_URL     = https://<provider-gateway>/claude
ANTHROPIC_AUTH_TOKEN   = sk-...
ANTHROPIC_MODEL        = claude-fable-5  (optional override)
```

These env vars are stored in CC-Switch's SQLite database, **not** in any \n`.json` or `.toml` file.

### ReClaude Daemon Troubleshooting

#### Checking Daemon Health

```bash
# 1. Check daemon state
cat ~/.reclaude/state.json
# Key fields:
#   daemon.running          — true/false
#   daemon.pid              — process ID
#   daemon.port             — API port
#   daemon.transparent_port — proxy port
#   gateway.healthy         — true/false
#   gateway.url             — gateway endpoint (regional)
#   last_error              — null or error message

# 2. Check daemon logs (appended; look for "已正常退出" as session boundary)
cat ~/.reclaude/logs/daemon.log | tail -30

# 3. Verify process is running
ps aux | grep reclaude
```

#### Common Errors

| Error | Code | Meaning | Recovery |
|-------|------|---------|----------|
| `device_revoked` | 401 | Device revoked on ReClaude server | Run `reclaude login` to re-authenticate |
| `gateway_unavailable` | 500 | Gateway API offline | Wait; check `gateway.url` in state.json; may be server-side outage |
| `auto-pick failed (no reachable candidates)` | — | All gateway candidates unreachable | DNS/network issue; daemon falls back to `www.reclaude.ai` |
| `lookup dl.reclaude.ai: no such host` | — | Update manifest server DNS dead | Non-critical — updates will fail but core function works |
| `spawn EINVAL` | EINVAL | Failed to spawn Claude Code child | Secondary effect of auth/gateway failure above |

#### Daemon Restart Procedure

```bash
# 1. Kill existing daemon(s)
kill <PID>    # or taskkill //F //PID <PID> on Windows

# 2. Start daemon fresh
"/c/Users/Administrator/AppData/Local/Programs/reclaude/bin/reclaude.exe" daemon

# 3. Wait 2-3 seconds, then verify
cat ~/.reclaude/state.json
# daemon.running → true, gateway.healthy → true

# 4. Check logs for errors
cat ~/.reclaude/logs/daemon.log | tail -5
```

#### Gateway Region Routing

The daemon auto-selects the best gateway. Common URLs:

| Gateway URL | Region |
|-------------|--------|
| `https://www.reclaude.ai` | Default / fallback |
| `https://asia.route.reclaude.ai` | Asia-Pacific |
| `https://dl.reclaude.ai` | Update manifest (may be dead) |

A healthy gateway shows `gateway.healthy: true` with a recent `last_check_at_ms`.

#### Full Recovery Sequence

When ReClaude won't open (typical cascade):

1. Kill existing daemon
2. Start daemon fresh
3. Check `state.json` → `gateway.healthy` should become `true` within seconds
4. If `device_revoked` → `reclaude login`
5. If `gateway_unavailable` persists → server infrastructure issue; use official `claude` as fallback
6. Official `claude` uses OAuth directly — no gateway dependency

---

## CC-Switch (provider switcher)

### DB location

```
~/.cc-switch/cc-switch.db
```

### Key tables

| Table | Contents |
|-------|----------|
| `providers` | Provider definitions with `settings_config` JSON column |
| `settings` | Global settings: `currentProviderClaude`, `currentProviderCodex` |
| `proxy_config` | Proxy mode, timeouts, failover |
| `provider_health` | Health check results per provider |
| `model_pricing` | Cost info: `claude-fable-5`, `claude-opus-4-8`, etc. |

### How to find current provider

Query the `settings` table:

```sql
SELECT value FROM settings WHERE key = 'currentProviderClaude';
-- Returns provider ID like "rightcode-1783706964495"

SELECT value FROM settings WHERE key = 'currentProviderCodex';
-- Returns provider ID like "mycodex-1783865031482"
```

Then look up the provider's `settings_config` JSON to get the env vars:

```python
import json, sqlite3
db = sqlite3.connect(r"C:\Users\<user>\.cc-switch\cc-switch.db")
cur = db.execute("SELECT settings_config FROM providers WHERE id=?", (provider_id,))
settings = json.loads(cur.fetchone()[0])
# env = settings.get("env", {})  →  ANTHROPIC_BASE_URL, etc.
```

### Provider `settings_config` structure

**Right Code** (Claude provider):
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://www.right.codes/claude",
    "ANTHROPIC_AUTH_TOKEN": "sk-..."
  }
}
```

**Generic proxy** (e.g., fkcodex):
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://www.fkcodex.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-...",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
    "ANTHROPIC_MODEL": "claude-fable-5"
  }
}
```

---

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

## Reverting Modifications (Config Restoration)

When a project (e.g., open-tgtylab) has modified AI tool configs and you need to restore them while preserving session data:

### Claude Code — `~/.claude/`

**Files installed by projects:**
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Ghost identity / jailbreak prompt (up to 80KB) |
| `system-prompt.md` | Model instructions override (up to 10KB) |
| `config.toml` | `model_instructions_file = "system-prompt.md"` |
| `settings.json` | Modified — adds bypassPermissions, mcpServers |
| `.claude/hooks/` | Pre-tool-call hooks |
| `.claude/workflows/` | Workflow JS files |
| `.claude/settings.local.json` | Permission bypass config |

**Restoration:**
1. Check `~/.claude/backups/` for pre-modification backup (saved by deploy script)
2. Restore `settings.json` from backup
3. Remove: CLAUDE.md, system-prompt.md, config.toml
4. Remove: `.claude/hooks/`, `.claude/workflows/`, `.claude/skills/`, `.claude/settings.local.json`
5. Keep: all session files (history.jsonl, sessions/, backups/)

### Claude Desktop (ReClaude) — `~/AppData/Roaming/claude/`

Same file list. Restoration:
1. Remove CLAUDE.md, system-prompt.md, config.toml
2. Clean settings.json — remove `permissions.defaultMode`, `mcpServers.reverse_lab_tools` block
3. Remove `.claude/hooks/`, `.claude/workflows/`, `.claude/settings.local.json`
4. Keep `claude_desktop_config.json` (user preferences) unchanged

### Codex — `~/.codex/`

**Files installed by projects:**
| File | Purpose |
|------|---------|
| `gpt5.5-unrestricted.md` | Jailbreak system prompt |
| `AGENTS.md` | Agent protocol / execution rules |
| `instructions.txt` | Same content as AGENTS.md |
| `config.toml` | Modified — adds model_instructions_file, mcp_servers |
| `skills/reverse-flow/` | Reverse engineering skill pack |

**Restoration:**
1. Remove: gpt5.5-unrestricted.md, AGENTS.md, instructions.txt
2. Restore config.toml — delete `model_instructions_file` line, remove `[mcp_servers.reverse_lab_tools]` block and its tools subsections, remove any open-tgtylab project trust entry
3. Remove `skills/reverse-flow/` if present
4. **Preserve ALL session data**: logs_2.sqlite, state_*.sqlite, sessions/, session_index.jsonl, history.jsonl, memories_*.sqlite, archived_sessions/

### Codex config.toml — specific cleanup

```toml
# DELETE this line:
model_instructions_file = "gpt5.5-unrestricted.md"

# DELETE this entire block and its [tools.*] subsections:
[mcp_servers.reverse_lab_tools]
command = "uv"
args = ["run", "--project", "...", "python", "..."]
startup_timeout_sec = 30

# DELETE if pointing at the modifying project:
[projects.'c:\\users\\administrator\\desktop\\open-tgtylab\\open-tgtylab']
trust_level = "trusted"
```

Keep everything else (model_provider, model_providers.custom, mcp_servers.node_repl, plugins, marketplace, burpsuite, features, windows, desktop, other project trusts).

---

## Switching from Relay/Proxy to Official Provider (Claude Code)

When a user wants to stop using a third-party relay (e.g. Right Code, fkcodex) and connect directly to the official Anthropic API:

### Step 1 — Identify the relay provider in CC-Switch

Check the CC-Switch `settings.json`:
```python
import json
s = json.load(open(r"C:\Users\<user>\.cc-switch\settings.json"))
print(s.get("currentProviderClaude"))  # e.g. "rightcode-1783706964495"
```

Resolve the provider ID to see its actual relay URL:
```bash
cd ~/.cc-switch
python3 -c "
import sqlite3, json
db = sqlite3.connect('cc-switch.db')
rows = db.execute(\"SELECT id, settings_config FROM providers WHERE app_type='claude'\").fetchall()
for rid, cfg in rows:
    env = json.loads(cfg).get('env', {})
    if env.get('ANTHROPIC_BASE_URL'):
        print(f'{rid}: base_url={env[\"ANTHROPIC_BASE_URL\"]}')
db.close()
"
```

Common relay patterns:
| Provider pattern | `ANTHROPIC_BASE_URL` | Relay type |
|---|---|---|
| Right Code | `https://www.right.codes/claude` | right.codes relay |
| fkcodex | `https://www.fkcodex.com` | fkcodex relay |
| aisz.mom | `https://api.aisz.mom/v1` | generic API relay |

### Step 2 — Verify official provider exists in DB

```bash
cd ~/.cc-switch
python3 -c "
import sqlite3
db = sqlite3.connect('cc-switch.db')
official = db.execute(\"SELECT id FROM providers WHERE id='claude-official'\").fetchone()
print('Official provider found:', official is not None)
db.close()
"
```

### Step 3 — Switch the provider via CC-Switch

**Three places need updating:**

```bash
cd ~/.cc-switch
python3 -c "
import sqlite3

db = sqlite3.connect('cc-switch.db')

# 3a. Update is_current flags
db.execute(\"UPDATE providers SET is_current=0 WHERE is_current=1 AND app_type='claude'\")
db.execute(\"UPDATE providers SET is_current=1 WHERE id='claude-official'\")

# 3b. Update settings table
db.execute(
    \"UPDATE settings SET value='claude-official' WHERE key='currentProviderClaude'\"
)
db.commit()

# Verify
rows = db.execute(\"SELECT id, is_current FROM providers WHERE app_type='claude'\").fetchall()
for r in rows:
    print(f'  {r[0]}: is_current={r[1]}')
db.close()
"
```

**3c. Update `~/.cc-switch/settings.json`:**
Replace the provider ID:
```json
"currentProviderClaude": "rightcode-1783706964495"  →  "currentProviderClaude": "claude-official"
```

### Step 4 — Clean up `~/.claude/settings.json`

Relay providers often write stale env overrides into Claude Code's own settings (custom model names, model aliases). Overwrite with clean defaults:
```json
{
  "skipDangerousModePermissionPrompt": true,
  "skipWorkflowUsageWarning": true
}
```

### Step 5 — Verify the switch

Check official OAuth token is intact:
```bash
python3 -c "
import json
cred = json.load(open(r\"C:\\Users\\<user>\\.claude\\.credentials.json\"))
print('OAuth:', 'claudeAiOauth' in cred)
print('Subscription:', cred.get('claudeAiOauth', {}).get('subscriptionType', 'N/A'))
"
```

Also check no stale ANTHROPIC_ env vars linger in the environment:
```bash
set | grep -i anthropic 2>/dev/null || echo "clean"
```

Then run `claude` — it will hit `https://api.anthropic.com` directly using the Max subscription.

### Pitfalls

- **CC-Switch `proxy_config` table**: The local proxy (`proxy_enabled=1, enabled=1`) is a *separate* mechanism from provider switching. Disabling the proxy alone does NOT stop the relay — you must switch the provider.
- **`is_current` is used by the daemon** — if settings.json says `claude-official` but the DB still has the relay as `is_current=1`, the daemon re-injects relay env vars on restart. Update BOTH.
- **`.claude/settings.json` env overrides take precedence over provider config** — even after switching the provider, stale env vars in settings.json can override model selection. Always clean this file.
- **CC-Switch settings table vs settings.json**: `currentProviderClaude` lives in BOTH the SQLite `settings` table and the `settings.json` file. Check both to confirm the switch took.
- **Right Code stores `ANTHROPIC_AUTH_TOKEN` in the provider config** — once you switch away, that token is no longer injected. The official OAuth token in `.credentials.json` takes over automatically.

### Reference

See `references/rightcode-relay-case-study.md` for a real-world transcript of removing the Right Code relay from Claude Code.
See `references/cc-switch-db-schema.md` for the full `providers` table schema, `meta.usage_script` balance-query pattern, and the clean-slate Codex `config.toml` recipe.

## IP Relay / Minimalist API Proxy Configuration

Some Chinese API proxies have NO dashboard, NO balance endpoint, NO auth endpoint — just a bare `/v1/models` and `/v1/chat/completions`. These need special handling.

### Characteristics
| Feature | Typical | This pattern |
|---------|---------|-------------|
| `/v1/models` | ✅ Works | ✅ Works |
| `/v1/dashboard/billing` | ✅ Usually present | ❌ Returns 404 |
| `/v1/chat/completions` | ✅ | ✅ |
| API key auth | `Bearer sk-...` | ✅ Standard |
| Usage/balance query | Available | ❌ Not available |

### CC-Switch Configuration (via DB)

```python
import sqlite3, json, time

db_path = r'C:\Users\Administrator\.cc-switch\cc-switch.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

provider_id = f"ip-relay-{int(time.time()*1000)}"

settings = {
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "sk-e6e35...",
        "ANTHROPIC_BASE_URL": "http://70.39.179.245:8080",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
        "ANTHROPIC_MODEL": "claude-fable-5"
    }
}

cursor.execute("""
    INSERT OR REPLACE INTO providers 
    (id, app_type, name, settings_config, website_url, category, created_at, 
     is_current, in_failover_queue, cost_multiplier)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    provider_id, "claude", "IP Relay",
    json.dumps(settings), "http://70.39.179.245:8080",
    None, int(time.time() * 1000), 1, 0, 1.0
))

conn.commit()
conn.close()
```

### Claude Code direct settings.json (no CC-Switch needed)

For users who don't use CC-Switch, just edit `~/.claude/settings.json`:

```json
{
  "model": "claude-fable-5[1m]",
  "effortLevel": "xhigh",
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-...",
    "ANTHROPIC_BASE_URL": "http://70.39.179.245:8080",
    "ANTHROPIC_MODEL": "claude-fable-5"
  }
}
```

### Parallel Claude + Codex Configuration

CC-Switch can configure BOTH Claude Code and Codex CLI with different providers in one session:

```python
# Add Claude provider
cursor.execute("INSERT INTO providers (...) VALUES (...) FOR claude")

# Add Codex provider with different endpoint
cursor.execute("INSERT INTO providers (...) VALUES (...) FOR codex")

# Set both as current
cursor.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'claude'")
cursor.execute("UPDATE providers SET is_current = 1 WHERE app_type = 'claude' AND id = ?", (claude_id,))
cursor.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'codex'")
cursor.execute("UPDATE providers SET is_current = 1 WHERE app_type = 'codex' AND id = ?", (codex_id,))
```

### API Key Verification (Quick Test)

```bash
# Test models endpoint
curl -s "$BASE_URL/v1/models" -H "Authorization: Bearer $KEY"

# Expected: {"data":[{"id":"claude-fable-5",...}]}
# 
# If 401: key expired or wrong format
# If 404/wrong content: URL might be wrong or proxy not OpenAI-compatible
# If timeout: proxy/network issue (may need proxy on 127.0.0.1:10808 in China)
```

### Pitfalls
- IP relays often have NO rate limiting info — you only discover you're out of quota when requests start failing
- Chinese IPs may need a proxy chain (127.0.0.1:10808) even to reach the relay
- `/v1/models` returning 200 does NOT guarantee `/v1/chat/completions` works — always test both
- Some relays return `experimental_bearer_token` as a required config field; others use `Authorization` header only

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

## CC-Panes Launch Profiles — dual relay (two 中转, pick per session)

CC-Panes (Tauri app) can run Claude Code against DIFFERENT relays in parallel sessions:
create one Provider + one Launch Profile per relay, then pick the profile when starting a
session. This is the "方案 B" answer to "终端输入 claude1 走中转1 / claude2 走中转2" — CC-Panes
has NO terminal-alias mechanism (`LaunchProfile.alias` is display-only).

### Key facts (from cc-panes source, Aug 2026)

- Config files live in the app data dir (`~/.cc-panes/` release, `~/.cc-panes-dev/` debug):
  - `providers.json` — `{"providers": [...], "defaultIsSystem": false}`
  - `launch-profiles.json` — `{"schemaVersion": 1, "profiles": [...]}`
- Provider JSON shape: `{"id","name","providerType":"proxy","apiKey","baseUrl","isDefault":false}`
  (camelCase). `providerType: "proxy"` injects `ANTHROPIC_API_KEY` + `ANTHROPIC_BASE_URL`
  into the launched CLI.
- **CRITICAL: CC-Panes injects `ANTHROPIC_API_KEY`, not `ANTHROPIC_AUTH_TOKEN`** — but
  new-api-family relays (fkcodex, etc.) accept the relay token as a Bearer `ANTHROPIC_API_KEY`
  header. Verified live: `POST {base}/v1/messages` with `Authorization: Bearer <relay token>`
  returns 200. So reuse the same token in `apiKey`.
- Launch Profile JSON shape:
  `{"id","name","alias","providerId","targetTools":["claude"],"targetRuntime":null,"yoloMode":false,"mcpPolicy":{...},"skillPolicy":{...},"isDefault":false,"createdAt","updatedAt"}`
- `ProviderService` calls `refresh_from_file()` before every read → providers.json edits are
  picked up live. `LaunchProfileService` loads at startup → **restart the app after writing
  launch-profiles.json** (and it's safer to restart for providers too; the frontend caches).
- Verification without GUI: the bundled web server exposes the same API at
  `http://127.0.0.1:18080/` (release) — `GET /api/providers`, `GET /api/launch-profiles`,
  `POST /api/launch-profiles/preview {"profileId":"...","cliTool":"claude"}` returns the
  resolved provider binding.

### Setup script pattern (read tokens from CC-Switch DB, write both files)

```python
import sqlite3, json, datetime
db = sqlite3.connect(r'C:\Users\Administrator\.cc-switch\cc-switch.db')
rows = db.execute("SELECT name, settings_config FROM providers WHERE app_type='claude'").fetchall()
# find each relay's env.ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL from settings_config JSON
providers = [{"id":"relay-1","name":"Claude中转1","providerType":"proxy",
              "apiKey":tok1,"baseUrl":url1,"isDefault":False}, {...relay-2}]
json.dump({"providers":providers,"defaultIsSystem":False}, open(r'~\.cc-panes\providers.json','w'))
profiles = [{"id":"relay-1-p","name":"Claude-中转1","alias":"claude1","providerId":"relay-1",
             "targetTools":["claude"],"mcpPolicy":{"mode":"default"},"skillPolicy":{"mode":"core"},
             "isDefault":False,"createdAt":now,"updatedAt":now}, {...}]
json.dump({"schemaVersion":1,"profiles":profiles}, open(r'~\.cc-panes\launch-profiles.json','w'))
```

### Pitfalls

- **Balance check**: relays built on new-api expose balance at `/api/user/self` but it needs
  the WEB-LOGIN session cookie, NOT the API key (API key → "Unauthorized, invalid access
  token"). `/dashboard/billing/credit_grants` returns the SPA HTML, not JSON. So CC-Panes /
  CC-Switch / API key cannot show relay balance — user must log into the relay's web panel.
- **HTTP 503 "No available accounts"** from a relay = the relay's own account pool is empty
  (auth passed, 401 would be auth failure). Not a config bug; tell the user to wait/top up.
- **WAF on Chinese relays**: plain `urllib` gets `403 error code: 1010` (Cloudflare) — send a
  desktop Chrome `User-Agent` header.
- 70.39-style bare relays (no dashboard, no /v1/models even) only serve `/v1/messages`-style
  endpoints; there is no balance API at all.

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

## CC-Panes process recovery (won't open / frozen window) — verified Aug 2026

CC-Panes is Tauri 2 + WebView2. Two distinct "broken" symptoms, two different fixes.
Install dir (release): `C:\Users\<user>\AppData\Local\cc-panes\cc-panes.exe`; data in
`~/.cc-panes/` (debug: `~/.cc-panes-dev/`).

### Symptom A — clicking the desktop icon does nothing ("打不开")

The old instance's process is ALIVE but its main window is hidden (`visible=False`);
the new instance exits within seconds via the **single-instance lock**. Don't relaunch
or kill — reveal the hidden window:

```powershell
# Get-Process cc-panes .MainWindowHandle may point at a 16×16 HELPER window
# (titled like "com.ccpanes.app-siw") — not the real one. EnumWindows the cc-panes
# PID and find the window titled "CC-Panes" (it may be fullscreen-sized but invisible).
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W32H {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
$h = [IntPtr]<real window hwnd, e.g. 11670950>
[W32H]::ShowWindow($h, 9)        # SW_RESTORE
[W32H]::ShowWindow($h, 5)        # SW_SHOW
[W32H]::SetForegroundWindow($h)
# verify: IsWindowVisible → True, GetWindowRect → full size
```

### Symptom B — window visible but drag / maximize / clicks dead

Main process `Responding=True`, but two `msedgewebview2` renderer processes each spin
~50% CPU → WebView2 renderer busy-loop; the UI is a static frame. Restart is the only fix:

```powershell
$p = Get-Process cc-panes; $p.CloseMainWindow(); Start-Sleep 3
if (!$p.HasExited) { $p.Kill() }                  # graceful first, force only if stuck
Stop-Process -Name cc-panes-daemon,cc-panes-web -Force   # orphans keep :18080 bound
# relaunch: & "$env:LOCALAPPDATA\cc-panes\cc-panes.exe"
# verify healthy: main CPU ≈0.06s/5s (~1%); no webview2 process >30% after settle;
#   netstat shows 127.0.0.1:18080 LISTENING again
```

### Pitfalls

- **Killing only the main process leaves orphans**: `cc-panes-daemon` + `cc-panes-web`
  survive and keep port 18080 bound; kill all three before relaunching.
- **`taskkill //F //PID` breaks under git-bash** (MSYS mangles `/F`). Use PowerShell
  `Stop-Process` instead.
- **Restart needs user consent**: this user's rule — always ask before
  kill/restart (they were burned by an unsanctioned kill of cc-panes).
- Single-instance lock means "won't open" is usually NOT a crash — check `tasklist |
  grep cc-panes` for a live process BEFORE assuming a corrupt install.

## Quick Reference: Where is model_provider?

| Tool | Config location | Provider mechanism |
|------|----------------|-------------------|
| **Claude Code** (official) | `~/.claude/.credentials.json` | OAuth → Anthropic API |
| **ReClaude** | `~/.cc-switch/cc-switch.db` | CC-Switch env vars → daemon proxy |
| **Codex** (official) | `~/.codex/config.toml` | `model_provider` + OAuth to OpenAI |
| **Codex** (custom) | `~/.codex/config.toml` | `model_providers.custom` section |
| **Hermes Agent** | `~/AppData/Local/hermes/profiles/<profile>/config.yaml` | `model.base_url` + `model.api_key` (provider: custom) |

## Pitfalls

- **Codex relay login loop**: relay config with `requires_openai_auth = true` (CC Switch writes this by default) forces the ChatGPT OAuth login flow even when a valid `experimental_bearer_token` is present. Stale/expired OAuth tokens in `~/.codex/auth.json` make it worse (endless "Failed to refresh token: 401 invalid_refresh_token"). Fix: set `requires_openai_auth = false` in `[model_providers.custom]`, back up and remove `~/.codex/auth.json`. Symptom: user sees "登录/重新登录" despite using a relay.
- **Hermes tool output redacts `sk-` API keys**: `read_file`/`grep`/terminal output shows keys as `«redacted:sk-…»` or `sk-Zwo...h16o` — the REAL key may be intact in the file/DB. Don't conclude "key lost" from redacted display; use `patch`/`diff` (which reveal actual content) or compare lengths to verify. The diff output of a patch shows the true bytes.
- **Missing `model_instructions_file` hard-errors codex**: if `model_instructions_file` points to a deleted file (e.g. jailbreak prompt cleaned up), `codex` refuses to start (`failed to read model instructions file`). Remove the line or restore the file.
- **`~/.claude/config.toml` is nearly empty for ReClaude users** — don't look 
  there for provider config; it only has `model_instructions_file`.
- **CC-Switch env vars are not in the shell environment** — they're injected 
  into the daemon process. Running `env | grep ANTHROPIC` in a regular 
  terminal shows nothing.
- **`currentProviderClaude` value in CC-Switch** is a generated ID like 
  `rightcode-1783706964495` — you must query the DB to resolve it.
- **`settings.json` vs `settings.local.json`** — both exist in `~/.claude/`.\n  `settings.local.json` holds permission allow-lists. The main `settings.json`\n  holds MCP servers and permission mode config.
- **`state.json` persists across sessions** — a stale `state.json` from a previous daemon may show old port numbers. The new daemon overwrites it on start.\n- **`gateway.healthy: true` is a snapshot** — it means the last health check succeeded, not current. Check `last_check_at_ms` for recency.\n- **Daemon.log appends, never rotates** — look for the `已正常退出` (clean exit) timestamp to find where the old session ended.\n- **`dl.reclaude.ai` DNS failure is non-critical** — update checks fail but daemon proxy works fine.\n- **OAuth credentials in `~/.claude/.credentials.json` work only through the ReClaude daemon** — direct `--backend anthropic` with OAuth returns 401. The token is not directly portable to the Anthropic SDK.
- **settings.json env overrides can break OAuth without CC-Switch** — stale `ANTHROPIC_MODEL` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_DEFAULT_*` env vars in `~/.claude/settings.json` force all requests through a custom relay (fkcodex, aisz.mom, etc.). This is a simpler route to a custom provider than CC-Switch: just the `env` block in settings.json. **Recovery**: strip the env block, set model to `opus[1m]` or `claude-sonnet-4-6-20251002`, verify `.credentials.json` has valid OAuth, then run `claude auth status`. No CC-Switch DB queries needed.
