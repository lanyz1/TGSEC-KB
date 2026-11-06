# Right Code Relay Case Study — Claude Code

## Background

The user had Claude Code configured through **CC-Switch** to route all API traffic through `https://www.right.codes/claude` (a third-party relay/middleman). They wanted to remove this relay and connect directly to the official Anthropic API using their existing Max subscription.

## Initial State

### CC-Switch settings.json
```json
{
  "currentProviderClaude": "rightcode-1783706964495",
  "enableLocalProxy": true
}
```

### CC-Switch DB providers table — Right Code entry
```json
{
  "id": "rightcode-1783706964495",
  "name": "Right Code",
  "settings_config": {
    "env": {
      "ANTHROPIC_AUTH_TOKEN": "sk-979...180e",
      "ANTHROPIC_BASE_URL": "https://www.right.codes/claude"
    }
  }
}
```

The injected env vars (`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`) made Claude Code send all requests to the Right Code relay instead of `https://api.anthropic.com`.

### `~/.claude/settings.json` (stale relay artifact)
```json
{
  "env": {
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-opus-4-8",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-opus-4-8",
    "ANTHROPIC_MODEL": "claude-opus-4-8"
  },
  "model": "claude-fable-5[1m]",
  "effortLevel": "high",
  "showThinkingSummaries": true,
  "skipDangerousModePermissionPrompt": true,
  "skipWorkflowUsageWarning": true
}
```

### `~/.claude/.credentials.json` (official auth — already present)
```json
{
  "claudeAiOauth": {
    "accessToken": "«redacted:sk-…»",
    "subscriptionType": "max",
    "scopes": ["user:inference", "user:profile", "user:sessions:claude_code", ...]
  }
}
```

The user was already logged into their official Max account, but the CC-Switch relay was intercepting all requests before they could reach Anthropic.

## Fix Applied

### 1. Switched CC-Switch provider

Updated `~/.cc-switch/settings.json`:
```json
"currentProviderClaude": "claude-official"
```

Updated DB:
```sql
UPDATE providers SET is_current=0 WHERE id='rightcode-1783706964495';
UPDATE providers SET is_current=1 WHERE id='claude-official';
UPDATE settings SET value='claude-official' WHERE key='currentProviderClaude';
```

### 2. Cleaned stale settings

Overwrote `~/.claude/settings.json` with minimal config:
```json
{
  "skipDangerousModePermissionPrompt": true,
  "skipWorkflowUsageWarning": true
}
```

### 3. Verified

- `claude-official` has `"env": {}` in its settings_config — no relay injection
- `proxy_config` for `claude` had `proxy_enabled=0, enabled=0` (already off)
- No `ANTHROPIC_BASE_URL` or `ANTHROPIC_AUTH_TOKEN` env vars in system/user scope
- Official OAuth token intact with `subscriptionType: "max"`

## Key Lessons

1. **CC-Switch has a redundant state problem**: the `currentProviderClaude` lives in BOTH the SQLite `settings` table AND the `settings.json` file. If only one is updated, the daemon may re-apply stale config on restart.

2. **`is_current` flag matters**: the `providers` table has an `is_current` column that the CC-Switch daemon queries. Even after updating settings.json, if the relay provider still has `is_current=1`, it gets re-selected on daemon restart.

3. **`proxy_config` is NOT the relay switch**: setting `proxy_enabled=0` only disables CC-Switch's local HTTP proxy (127.0.0.1:15721). It does NOT prevent the env-var injection from the provider config. Provider switching is the correct mechanism.

4. **`.claude/settings.json` collects leaky artifact**: relay providers sometimes write their model aliases into this file (e.g. `"model": "claude-fable-5[1m]"`). These must be cleaned manually after the switch.

5. **Official provider has empty env**: `claude-official`'s `settings_config` is `{"env":{}}` — no `ANTHROPIC_BASE_URL` override means Claude Code falls back to `https://api.anthropic.com`.
