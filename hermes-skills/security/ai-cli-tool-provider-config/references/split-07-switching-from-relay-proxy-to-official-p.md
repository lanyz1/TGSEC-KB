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

