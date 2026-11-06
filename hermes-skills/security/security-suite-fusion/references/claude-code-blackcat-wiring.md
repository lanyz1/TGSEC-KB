# Claude Code live-pentest (Black-cat)

1. `npm i -g @anthropic-ai/claude-code`
2. Vendor → `.claude/skills/pentest-redteam/` + `hermes-skills/pentest-redteam/`
3. SessionStart → `case_ledger.py context case`
4. Execute-first `CLAUDE.md`
5. After every sync: `bash scripts/ensure-claude-pentest.sh`
6. `cd <suite> && claude` → `/skill pentest-redteam`

Ammo via `TGSEC-BRIDGE.md` → `domains/` + `poc-catalog`.
