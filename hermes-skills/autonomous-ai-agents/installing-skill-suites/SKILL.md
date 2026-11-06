---
name: installing-skill-suites
description: "安装第三方技能套件到 Hermes"
---

# Installing third-party skill/knowledge suites into Hermes

Procedure first, then pitfalls.

## Procedure

1. **Never pipe `curl | bash`.** Fetch the script to a file and read it fully before deciding to run it: `curl -fsSL <url> -o <scratch>/x.sh` then read the file.
2. **Verify the repo/owner actually exists and matches what the user referenced.** Lookalike URLs (owner or repo name off by one character) 404 or point elsewhere. Check `curl -s -o /dev/null -w "%{http_code}" <url>` and list real contents via `api.github.com/repos/<owner>/<repo>/contents/<path>`.
3. **Read the installer and its downstream scripts before running.** Installers are thin wrappers: clone + run a `bootstrap.sh`, which runs sync scripts and possibly a persona/memory installer. Enumerate the full side-effect surface: clone target, what gets synced into `~/.hermes/skills/`, and whether anything writes `~/.hermes/memories/` or persona files (`~/.hermes/SOUL.md`, top-level `USER.md`).
4. **Protect local memory/persona.** If any step copies a payload over `~/.hermes/memories/USER.md`/`MEMORY.md`, neutralize that step — e.g. `mv <setup.sh> <setup.sh>.DISABLED` so the bootstrap skips it — instead of letting it clobber then restoring. Back up `~/.hermes/memories/` first as insurance.
5. **Confirm the sync mode.** Overlay (`rsync -a`, no `--delete`) keeps private local skills; prune (`--delete`) wipes extras. Prefer overlay.
6. **Run, then verify the effect — not the printed messages.** Installers print success lines even for steps that were skipped (e.g. "✓ Hermes memories" when the memory script was absent). Verify skills with `find <dest> -name SKILL.md | wc -l`, and memory intact via `ls -la` mtime + content.
7. **Tell the user new skills need a fresh session.** The Hermes skill directory is cached and won't load new entries mid-session.

## Pitfalls

- **Installer scripts hardcode their own repo URL** (often an env-var default) that can be dead or different from the repo the user actually referenced. Read the script's default URL; don't trust the README's install line.
- **A suite's bootstrap can silently overwrite `~/.hermes/memories/USER.md`/`MEMORY.md`** with its own persona payload. A "keep existing if larger" guard only protects a LARGER existing file, so a small personalized file still gets clobbered. Disable the step; don't rely on the guard.
- **Missing `rsync` changes the fallback result.** Without it, sync falls back to `cp -a`, which copies everything (including README.md) and applies no `--delete`/`--exclude`. Install rsync for the documented prune/exclude behavior, else verify what the fallback actually copied.

## Direct copy for bare Agent-Skills-format bundles (no installer)

When the source is NOT an installer-based suite but a bare directory of Agent Skills (each `SKILL.md` with YAML frontmatter `name` + `description`), skip the installer workflow — the frontmatter is already Hermes-compatible:

1. **Unzip to scratch**, read INDEX/README to map structure (router vs playbook vs legacy vs agent-orchestrator).
2. **`skills_list` first to diff against the existing library** — import only genuine increments, skip:
   - legacy versions (e.g. `-testing` suffix, already superseded by a same-name playbook)
   - skills already covered by the current library (e.g. Web-vuln classes already in hack-skills/web-sec)
3. **`cp -r <skill-dir> ~/.hermes/skills/<category>/`** per skill (batch in a `for` loop).
4. **`skills_list` to verify** descriptions load fully (not empty/truncated).
5. New entries still need a fresh session to become active in-context.

Pitfall: big suites ship legacy + overlapping skills; full-copy bloats the library and re-implements what exists. Diff first, import only increments — the user explicitly wants增量导入、重复跳过, not a stack dump.

## References
- `references/tgsec-suite.md` — TGSEC 渗透套件 recipe: correct repo, known URL bug, memory-overwrite location, install/update commands.
