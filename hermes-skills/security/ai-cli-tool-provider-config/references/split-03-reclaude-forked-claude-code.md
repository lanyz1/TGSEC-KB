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

