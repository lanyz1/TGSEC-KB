# open-tgtylab MCP + Config Deployment (July 2026)

## What Was Deployed

The open-tgtylab project (https://github.com/GeniusHu-tgty/Open-tgtylab) — a multi-platform AI-driven security research toolchain.

### Components

| Component | What It Is | Windows Path |
|-----------|-----------|--------------|
| **ReverseLabToolsMCP** | Python FastMCP server (1782 lines), 105 tools | `C:/Users/.../tools/skills/mcp/ReverseLabToolsMCP/` |
| **CLAUDE.md** | Ghost identity (79KB) | `~/.claude/CLAUDE.md` |
| **settings.json** | bypassPermissions + MCP registration | `~/.claude/settings.json` |
| **system-prompt.md** | English Ghost prompt | `~/.claude/system-prompt.md` |
| **SOUL.md** | Hermes Ghost identity (77KB) | `~/.hermes/SOUL.md` |
| **config.yaml** | Hermes auto-approve | `~/.hermes/config.yaml` |
| **Workflows** | 15 CTF automation JS files | `~/.claude/.claude/workflows/*.js` |
| **Hooks** | pre-tool-call.sh | `~/.claude/.claude/hooks/` |
| **Python RE libs** | lief, frida, angr, capstone, keystone, unicorn, pycryptodome | System Python |

### Deployment Order

```bash
# 1. MCP dependencies
uv sync --project "C:/.../ReverseLabToolsMCP"

# 2. Python RE libraries
python -m pip install lief frida angr capstone keystone-engine unicorn pycryptodome

# 3. settings.json - write with bypassPermissions + mcpServers.reverse_lab_tools
#   (absolute forward-slash paths, uv run command)

# 4. Copy config files to ~/.claude/, ~/.codex/, ~/.hermes/
# CLAUDE.md, system-prompt.md, config.toml, SOUL.md, config.yaml

# 5. Verify MCP server loads
uv run --project . python -c "from reverse_lab_tools_mcp import mcp; print(len(mcp._tool_manager.list_tools()))"
# → 105 tools
```

### Fix Applied

**Python 3.11 f-string backslash error** in `reverselab_mcp/tools/android_mumu.py` line 120:

```python
# Before (SyntaxError on Python 3.11):
wrapped = command if as_root else f"su -c \"{command.replace('\"', '\\\"')}\""

# After:
escaped = command.replace('"', '\\"')
wrapped = command if as_root else f'su -c "{escaped}"'
```

### Verification

```bash
# Python libraries
python -c "import lief; print(lief.__version__); import frida; import angr; import capstone; import unicorn; from Crypto.Cipher import AES; print('OK')"

# MCP tools loaded
uv run --project . python -c "from reverse_lab_tools_mcp import mcp; tools=mcp._tool_manager.list_tools(); print(len(tools), 'tools')"

# Settings check
python -c "import json; d=json.load(open(r'$HOME/.claude/settings.json')); print(d['permissions']['defaultMode']); print(list(d['mcpServers'].keys()))"
# → bypassPermissions, ['reverse_lab_tools']
```
