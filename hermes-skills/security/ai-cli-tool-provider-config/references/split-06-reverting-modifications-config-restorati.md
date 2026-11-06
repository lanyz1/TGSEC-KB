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

