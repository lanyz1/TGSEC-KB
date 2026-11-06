# Stop-all + aggressive cleanup — 2026-09-17

## Cron-before-kill (hard lesson)
User asked 「停止所有任务」 / cleared disk, then got a Cronjob Response from `opensms 广度优先喷口令看门狗` (`a8b3e40ecc07`, every 5m, `opensms_fast_watch.py`, no_agent) that respawned `brute_breadth.py`. Process kills alone looked successful; cron resurrected the job.

Order that actually works:
1. `cronjob(action='list')`
2. `remove` every campaign job (`opensms_*`, spray watchdogs, DNS drift monitors, airdrop watches)
3. Kill PIDs from `scripts/scan_procs.py` (SIGTERM then SIGKILL leftovers)
4. Re-list cron (expect 0 campaign jobs) + re-scan /proc
5. Only then archive/delete disk

「停止所有」 on this box also meant removing the remaining `airdrop888-watch`, not leaving one behind.

## Aggressive cleanup defaults (user chose 「激进」)
When disk panic + user picks aggressive:
- ARCHIVE then DELETE old campaign dirs under `/root/cases/` (77zhanghao, worldxpp, 1airdrop, airdrop888, gouzi888, …)
- Trim current campaign bulky subdirs (xc/, chrome-profile*, source clones, huge jsonl)
- Delete `/root/chrome`, tmp playwright profiles, hermes `state.db.corrupt_*`
- `journalctl --vacuum-size=50M`; truncate rotated `btmp.1`
- KEEP: tools/, security-suite/, go/, pwenv/, nuclei-templates/, botA/botB, gateway/mysqld/tor
- Archive root: `/root/reports/old-campaigns/<label>/`; manifest: `/root/deep-cleanup-manifest-<date>.md`
- Spot-verify REPORT*.md + token files in archive before `delete` phase

## Receipt
Always MEDIA the manifest. Report before/after `df -h /`, freed ~size, cron=0, attack procs=0, services still up.
