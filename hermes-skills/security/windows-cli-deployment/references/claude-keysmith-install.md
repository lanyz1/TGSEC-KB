# claude-keysmith Install Audit Workflow

**Source:** https://github.com/Jia-Ethan/claude-keysmith  
**Script:** `claude-instruct.py` — single-file Python CLI (no external dependencies)  
**License:** MIT

## What It Does

Manages Claude Code `CLAUDE.md` import blocks by:
1. Writing a separate instruction `.md` file under `~/.claude/keysmith/<name>.md` (user scope) or `<repo>/.claude/keysmith/<name>.md` (project/local scope)
2. Inserting a self-identifying managed import block into the target `CLAUDE.md` / `CLAUDE.local.md`

The import block format:
```markdown
<!-- claude-keysmith:start name=<name> -->
@keysmith/<name>.md
<!-- claude-keysmith:end name=<name> -->
```

## Supported Scopes

| scope | memory file | instruction file | import prefix |
|-------|-------------|-----------------|---------------|
| user | `~/.claude/CLAUDE.md` | `~/.claude/keysmith/<name>.md` | `@keysmith/` |
| project | `<repo>/CLAUDE.md` | `<repo>/.claude/keysmith/<name>.md` | `@.claude/keysmith/` |
| local | `<repo>/CLAUDE.local.md` | `<repo>/.claude/keysmith/<name>.md` | `@.claude/keysmith/` |

## Install Audit Checklist

### 1. Read the Source
- Read `README.md` first — understand scope, safety defaults, commands
- Read `claude-instruct.py` — verify no binary patching, no network calls, no credential storage
- Read `tests/test_claude_instruct.py` — verify test coverage of safety boundaries

### 2. Static Audit (Key Safety Checks)
- [ ] No modification of Claude Code binary
- [ ] No modification of `settings.json`, MCP, token, or cookie files
- [ ] No network interception
- [ ] No modification of running processes
- [ ] `--name` validated against path-traversal regex: `^[A-Za-z0-9._-]+$`
- [ ] Atomic writes via `tempfile.NamedTemporaryFile` + `os.replace`
- [ ] Backups via `shutil.copy2` with timestamp suffix before overwrite
- [ ] Dry-run by default; needs `--yes` to write
- [ ] `uninstall` removes only its own managed block (matched by `<!-- claude-keysmith:start/end -->` markers)
- [ ] `--dry-run` + `--yes` → `--dry-run` wins (safety-first)

### 3. Syntax Check
```bash
python3 -m py_compile claude-instruct.py
```

### 4. Run Static Tests
```bash
python3 -m pytest tests/
```

### 5. Dry-Run (no --yes)
```bash
python3 claude-instruct.py install --scope user --name my-rules
```
Expected output: `[DRY RUN]` header, scope info, memory file path, instruction file path, import target, memory change flag, instruction bytes, no file writes.

### 6. Verify Current State
Before writing, check:
- Does `~/.claude/CLAUDE.md` exist? (If yes, it will be backed up)
- Does `~/.claude/keysmith/` exist?
- Does the target instruction file already exist?

### 7. Write (with --yes)
Only after user confirmation. The script will:
- Backup existing `CLAUDE.md` (if any) to `CLAUDE.md.bak_YYYYMMDD_HHMMSS`
- Backup existing instruction file (if any)
- Write the instruction file atomically
- Write/update the import block in `CLAUDE.md` atomically

### 8. Verify After Install
```bash
cat ~/.claude/CLAUDE.md
cat ~/.claude/keysmith/<name>.md
```

## Windows Path Quirk

MSYS bash maps `/tmp` to a different path than what Python's `tempfile.gettempdir()` returns. When passing `--file`, use the Windows native path (e.g., `C:\Users\<user>\AppData\Local\Temp\`) rather than `/tmp/` to avoid `FileNotFoundError`.

## Commands Reference

```bash
# Install (dry-run by default)
python3 claude-instruct.py install --scope user --name rules --file ./rules.md

# Install (with confirmation)
python3 claude-instruct.py install --scope user --name rules --file ./rules.md --yes

# Status check
python3 claude-instruct.py status --scope user --name rules
python3 claude-instruct.py status --scope user --name rules --json

# Uninstall (dry-run by default)
python3 claude-instruct.py uninstall --scope user --name rules

# Uninstall (with confirmation)
python3 claude-instruct.py uninstall --scope user --name rules --yes

# Restore from backup
python3 claude-instruct.py restore --target ./CLAUDE.md --backup ./CLAUDE.md.bak_20260629_120000 --yes
```
