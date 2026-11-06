---
name: security-suite-fusion
description: "Use when fusing repos into TGSEC or Claude open-fire."
version: 1.0.0
---

# TGSEC Suite Fusion & Claude Open-Fire

Absorb external security repos into `/root/TGSEC-Qtzuu` and wire Claude Code
for authorized live pentest (Black-cat pattern).

## User corrections (bind)

1. **Self-intro / fusion notes** — only `README.md` + `START.md`. Bullets =
   **what was merged** only. Never source repo names or process meta.
2. **Complete 0day/POC/CVE** — INDEX-only rejected. Fill
   `domains/0day-exploits/poc-catalog/` (trees + CVE cards + JSONL).
3. **High-risk skills** — unlimited/phishing/opsec → `skills-restricted/`
   (+ skills-full) when user wants complete absorb.
4. **Claude cannot open-fire** — fix wiring: full `pentest-redteam` +
   SessionStart + execute-first `CLAUDE.md`.

## Absorb steps

1. Clone/extract → inventory → **diff** vs absorbed paths.
2. Fuse by attack surface into `domains/<face>/` — no stacking.
3. POC dumps: `references/complete-poc-cve-absorb.md`.
4. README/START content-only bullets + `domains/FUSION-YYYYMMDD-*.md`.
5. Commit/push; `sync-hermes-skills.sh` and/or `ensure-claude-pentest.sh`.

## Claude open-fire

See `references/claude-code-blackcat-wiring.md`.

```bash
npm i -g @anthropic-ai/claude-code
cd /root/TGSEC-Qtzuu && bash scripts/ensure-claude-pentest.sh
claude   # /skill pentest-redteam
```

## Pitfalls

- `sync-agent-skills` can wipe `.claude/skills` — always re-run ensure.
- WeChat/网盘 zip may ≠ article claim — unzip+diff first.
- Upstream 404 → alternate PoCs + `FAILED-CVE-FETCHES.md`.
- Hermes `black-cat-redteam` (thin) ≠ Claude `pentest-redteam` (full).
