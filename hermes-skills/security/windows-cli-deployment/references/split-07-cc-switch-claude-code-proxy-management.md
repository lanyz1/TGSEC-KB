## CC Switch — Claude Code Proxy Management

**CC Switch** (Claude Code Switch) is a community tool that simplifies switching between Claude Code proxy configurations. It's commonly used with Chinese 中转站 platforms like Right Code.

### Typical CC Switch + Proxy Workflow

1. Install CC Switch and configure it with your proxy settings
2. CC Switch sets `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` automatically
3. Start Claude Code (`claude`) — it inherits the proxy config from the environment
4. In Claude Code, verify with `/model` to see available models through the proxy

### CC Switch vs Direct SDK Calls

| Approach | Proxy Compatibility | Client Detection | Use Case |
|----------|-------------------|-----------------|----------|
| **CC Switch + real Claude Code CLI** | Full — proxy trusts real Claude Code binary | ✅ Passes JA3 fingerprint check | Production use with 中转站 |
| **@anthropic-ai/sdk (Node.js)** | Limited — proxy detects non-Claude-Code client | ❌ Blocked by fingerprinting | Development/testing only |

**Key insight**: If a proxy rejects Node.js SDK calls with "检测到客户端存在异常", the fix is to use the real Claude Code CLI (via CC Switch), not to patch the SDK headers.

