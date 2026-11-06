# safe-bulk-cleanup 全文 第 4/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## Files
- `references/cleanup-verification.md` — seven-layer post-stop verification matrix: systemd respawn, credential redaction, target-residue register
- `references/three-plane-teardown-20261019.md` — local host / target-side / agent `state.db` teardown: WARP mask repair, deleted-case-vs-surviving-ID-29 split, schema probe
- `scripts/scan_procs.py` — kill-safe /proc process finder
- `references/post-teardown-disk-cleanup-20261021.md` — reports-only retention + second-pass loose-file sweep; 2.3G archive + 686M `/tmp` staging deleted, 7.1G→10.4G
- `references/case-root-purge-20261021.md` — whole `/root/cases` purge after explicit 全部都清: one scope confirmation, 95,077-file preflight, 12G delete, 75%→51%, audit outside the deleted tree
- `scripts/roots_purge_preflight.sh` — read-only preflight for a case root: sizes, file count, top-level inventory, `/proc` cwd hits, cron/path references
- `templates/cleanup_two_phase.py` — archive→verify→delete script with manifest
- `references/workstation-2026-09-cleanup.md` — box layout, keep-list, archive conventions, 2026-09-11 deep-clean run log
- `references/stop-all-and-aggressive-cleanup-20260917.md` — cron-before-kill + aggressive archive/delete defaults from 2026-09-17
- `references/aggressive-cleanup-20260920.md` — 712win3 stop+trim + Playwright/Camoufox reclaim (~3G) run log
- `references/campaign-teardown-20260927.md` — close-out of a multi-week gambling-platform campaign: browser/tunnel/cron teardown, handoff-receipt convention, confirmed-vs-disproven ledger
- `references/shared-agent-host-deletion-scope.md` — multi-bot shared host: hot-zone cwd/fd map, 4-check ownership attribution, borrowed-key rule, retire-vs-keep verdicts, archive-then-delete retire protocol, state.db read-only pragma discipline (2026-10-10 full run: 93%→80%, 9 cases retired, zero other-bot impact)
- `references/git-repo-size-audit-20261002.md` — git repo bloat audit end-to-end: tracked/history/dup-blob inventory, PDF↔md twin statistical verification, two-tier measured filter-repo rewrite (291.08→52.17 MiB pack, 2,396 files), executed force push + fresh-clone read-back, .gitignore hardening
- `scripts/git_repo_audit.py` — re-runnable git repo bloat inventory: tracked sizes, same-SHA mirror dirs, history-only blobs, deletable-group rollup, measured vs estimated savings
- `scripts/git_history_rewrite.sh` — the execution half: dirty-check → timestamped backup → N `filter-repo` passes → `reflog expire`+`gc` → keep-list/size assertions, then (with `PUSH=1`) force push + `git ls-remote`/shallow-clone read-back
- `scripts/repo-poc-gate.sh` — copy into the target repo as `scripts/check-large-files.sh`: CI/pre-push gate, FAIL on demo media + duplicate skill mirrors, WARN on PoC weapon binaries (apk/exe/dll/zip are the payload, not junk — a naive >500KB gate false-Fails 13 of them and gets deleted by the repo owner)
- `references/disk-full-emergency-20261015.md` — disk-at-100% emergency on the shared multi-bot box (367M→6.1G over two passes): wave order, ownership forensics (`drfmud7h5b2n`=main case, `tato`=zhitian), comm/md5 verify-before-delete, gzip-in-place, swapfile shrink, old-kernel sim-gate purge, uv tools-vs-cache layout, sparse-ghost log, full-disk 300M+ survivor inventory, numbers discipline

