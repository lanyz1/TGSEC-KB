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

