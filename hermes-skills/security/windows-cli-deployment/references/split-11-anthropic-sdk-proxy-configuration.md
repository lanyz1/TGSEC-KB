## Anthropic SDK Proxy Configuration

When deploying tools that use `@anthropic-ai/sdk` through a proxy/中转 API service (e.g., Right Code, API aggregators), additional patches beyond Windows path fixes are needed.

### 1. baseURL Configuration

The `@anthropic-ai/sdk` accepts a `baseURL` option. Add environment variable support:

```javascript
function makeClient(auth) {
  const opts = {
    // ... other options
    baseURL: process.env.ANTHROPIC_BASE_URL || undefined,  // ADD THIS
  };
```

Set via environment:
```bash
set ANTHROPIC_BASE_URL=https://right.codes/claude
```

### 2. authToken vs apiKey

The SDK's `makeClient` has two auth modes that send different HTTP headers:

| Mode | Header | When Used |
|------|--------|-----------|
| `apiKey` (default) | `x-api-key: <token>` | Official Anthropic API |
| `authToken` | `Authorization: Bearer <token>` | Claude Code OAuth, some proxies |

**Problem**: Proxies like Right Code expect the `authToken` format even when using an API key, because they clone the Claude Code protocol.

**Fix**: Detect proxy URLs and switch to authToken mode, including the OAuth beta header:

```javascript
// In makeClient():
const baseUrl = (process.env.ANTHROPIC_BASE_URL || '').toLowerCase();
const isProxy = baseUrl.includes('proxy') || baseUrl.includes('right.codes');

if (auth.mode === 'oauth') {
  // Standard OAuth mode
  opts.authToken = auth.token;
  opts.apiKey = null;
  opts.defaultHeaders['anthropic-beta'] = OAUTH_BETA;
} else if (isProxy) {
  // Proxy mode: use authToken format + OAuth headers
  opts.authToken = auth.token;
  opts.apiKey = null;
  opts.defaultHeaders['anthropic-beta'] = OAUTH_BETA;
} else {
  // Standard API key mode
  opts.apiKey = <REDACTED>;
}
```

### 3. System Prompt Prefix (OAuth Mode)

OAuth tokens are ONLY accepted when the system prompt starts with exactly:
```
You are Claude Code, Anthropic's official CLI for Claude.
```

The `systemFor(auth, instructions)` function enforces this. When patching for a proxy, ensure this prefix is still set on auth ping requests.

### 4. Proxy Client Fingerprinting

Some proxies (Right Code) perform **deep client fingerprinting** beyond just headers. They check:
- TLS/JA3 fingerprint of the HTTP client
- Exact header order and values
- Request timing patterns

**Symptoms**: HTTP 400 with `"我们检测到您的客户端存在异常"` or `"请使用标准 Claude Code 客户端请求"`.

**Limitations**: Node.js's built-in `fetch` / `https` module has a different TLS fingerprint than the real Claude Code CLI. If the proxy does JA3 fingerprinting, changing headers alone won't bypass it — the client must be the real Claude Code binary.

**Workarounds** (in priority order):
1. Install the real Claude Code CLI and configure its proxy settings
2. Use an API-only proxy (one that accepts standard `x-api-key` auth)
3. Use the official Anthropic API directly

### 5. Model Name Mismatch

Proxies may not support all model IDs. Always check which models are available on the specific endpoint:

```bash
# Common proxy model IDs vs official:
# Official: claude-sonnet-4-20250514
# Proxy may require: claude-sonnet-4-6
# Ping model: claude-haiku-4-5-20251001
```

The tool's `PING_MODEL` constant must match a model available on the proxy endpoint. If the ping fails, either change the model or the endpoint.

### 6. Environment Variable Setup on Windows

When running via Python `subprocess`, environment variables must be passed explicitly — `shell=True` with `set VAR=val && cmd` can cause spaces in values:

```python
# BAD: trailing spaces can creep in with shell=True
subprocess.run('set KEY=val && node tool.mjs', shell=True, ...)

# GOOD: pass env explicitly
env = os.environ.copy()
env['ANTHROPIC_API_KEY'] = 'sk-...'
env['ANTHROPIC_BASE_URL'] = 'https://right.codes/claude'
subprocess.run(['node', 'tool.mjs'], env=env, ...)
```

