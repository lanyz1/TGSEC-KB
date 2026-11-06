# Post-ingest path audit

Absorbing a repo is not finished when the card exists. Every path in a card is a
promise; a dead path makes the technique unusable even when the write-up is good.

## Audit sequence

1. Inventory literal paths in each new/merged `SKILL.md` and its references:
   `/root/...`, `tools/...`, `docs/...`, `scripts/...`, `references/...`, `./data/...`.
2. Resolve every one against the **actual** repo root, not the root the upstream
   README claims. Use `test -e`, `find`, or Python `Path.exists()`.
3. Classify each miss:
   - old repo root → fix the root once, then re-scan;
   - helper script/doc genuinely absent → add a loud warning and a fallback command;
   - example/optional path → mark as optional, do not present it as runnable.
4. Never leave a dead `run:` line. Replace it with a command that resolves today, or
   remove the line and route to the live index (`vuln_find` / `repo_find`).
5. Rebuild and regress-test:
   ```bash
   python3 /root/.hermes/arsenal/arsenal_build.py
   python3 /root/.hermes/arsenal/vuln_build.py
   python3 /root/.hermes/arsenal/repo_build.py
   python3 /root/.hermes/arsenal/selftest.py   # must stay route-hit 30/30
   ```

## Case: `/root/security-suite`

- Upstream 0day cards pointed at `/root/security-suite`; the directory did not exist.
- Real tree: `/root/TGSEC-Qtzuu/domains/0day-exploits` (135MB, 13,686 files,
  960 product-CVE dirs, 1,189 Python files).
- Fixed 19 skill files by replacing the root, then rewrote the 0day card's usage
  section to go through `vuln_find` instead of assuming a fixed layout.
- A second class of misses: `tools/1day-kit/od_kit.py` and `docs/playbooks/*` were
  absent from the repo entirely. These cannot be fixed by changing a root; the card
  now carries an explicit warning and falls back to `vuln_find`.

## Rules

- **Count before bulk replace.** grep the old root across all skill files, count hits,
  patch, then grep again for zero.
- **Do not silently drop a broken reference.** Either repair it or mark it; a future
  session will trust an unmarked path.
- **Path audit is separate from tool provisioning.** Missing binary → `tool_get`;
  missing repo artifact → warning + alternate route.
