## MCP FastMCP Server Deployment on Windows

Deploying Python-based MCP (Model Context Protocol) servers (FastMCP) on Windows follows a different pattern than Node.js CLI tools.

### Prerequisites

- Python 3.10+ (Python 3.11 is common on Windows)
- `uv` package manager
- The MCP project with `pyproject.toml` and `uv.lock`

### Deployment Steps

```bash
# 1. Sync dependencies (creates .venv if needed)
uv sync --project "C:/path/to/mcp-project"

# 2. Verify module loads
cd "/c/path/to/mcp-project"
uv run --project . python -c "from your_mcp import mcp; print('OK')"
```

### Configuring in settings.json

```json
{
  "mcpServers": {
    "server_name": {
      "command": "uv",
      "args": [
        "run", "--project", "C:/absolute/path",
        "python", "C:/absolute/path/server.py"
      ],
      "env": {}
    }
  }
}
```

**Critical path rules:**
- Use forward slashes (`C:/path`) NOT backslashes
- `--project` and `python` args must be ABSOLUTE paths
- `uv` must be on PATH (verify with `which uv`)

### Permission Bypass

```json
{
  "permissions": { "defaultMode": "bypassPermissions" },
  "skipDangerousModePermissionPrompt": true
}
```

### Common MCP Module Errors on Python 3.11

**SyntaxError: f-string expression part cannot include a backslash**

```python
# ❌ Python 3.11 SyntaxError:
wrapped = f"su -c \"{command.replace('\"', '\\\"')}\""

# ✅ Fix: extract to variable first:
escaped = command.replace('"', '\\"')
wrapped = f'su -c "{escaped}"'
```

Python 3.11 does not allow backslashes inside f-string `{}` expressions (fixed in Python 3.12). Always extract expressions with backslash sequences into named variables before using in f-strings when targeting Python 3.10/3.11.

**ModuleNotFoundError after uv sync:**
- Check Python version: `uv run --project . python --version`
- Force venv Python: `uv venv --python 3.11 && uv sync`

See `references/opentgtylab-mcp-deployment.md` for a concrete MCP deployment case study (105 tools, Python 3.11 f-string fix, multi-platform config deployment).

