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

