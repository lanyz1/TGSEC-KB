# Workstation cleanup run — 2026-09-11 (Telegram "擎天柱" operator box)

## Box layout (verify before assuming)
- 3 Hermes profiles share /root: default (this chat), /root/.hermes-botA, /root/.hermes-botB — resident gateways; **never touch**, read-only checks only.
- Services to re-verify after any cleanup: hermes gateways (`pgrep -af 'hermes.*gateway'`), trae server (/root/.trae-server node procs), MySQL (BT panel: mysqld_safe + mysqld, socket /tmp/mysql.sock, port 3306), tor.
- /tmp infrastructure never in scope: *.sock (mysql.sock, php-cgi-74.sock, site_total.sock), systemd-private-*, snap-private-tmp, rockyou.txt.

## Conventions
- Archive root: `/root/reports/old-campaigns/<label>/` — per-campaign folders, ≤256K non-binary files (reports, creds, cookies, loot, audit scripts).
- Manifests: `/root/deep-cleanup-manifest-<date>.md`; earlier sweeps e.g. `/root/tmp-cleanup-manifest-20260911.txt`.
- Two sweeps this day: (1) /tmp root files — 1,972 entries / 72MB (kept rockyou.txt, venvs, campaign dirs, sockets); (2) deep sweep ~6G, 0 errors; disk 83% → 72% (8.4G → 14G free).

## Deep sweep contents
- _kb_ingest_20260908/10 (3G) — KB ingest staging, already absorbed (catalog refreshed 06:34).
- cmsnt-src (2G) — panel source dump; audit scripts + READMEs archived to old-campaigns/cmsnt-audit/.
- security-suite.bak.20260904065637 (63M) + hermes-backup (44M) + hermes-reinstall-backup — stale Sep-4 backups (suite is git-backed).
- 11 × *-pentest workspaces (433M; sf8709 379M) → small files archived (32 archive dirs / 39M total).
- 20 × /tmp campaign dirs (~475M; skhe_roslyn1 429M) → same archive treatment.
- /root/.hermes/state.db.corrupt_* ×4 (+wal) 130M — corrupt rebuild corpses.
- Kept: /root/tools (SecLists 2.5G + jadx), security-suite, skill-source repos (AboutSecurity, Black-cat, Claude-BugHunter, SecAtlas, Stopen, TORCH, exploitarium, hack-skills, reverse-skill(s), web-sec, SQL-Wordlist), go/, nuclei-templates/, epusdt-v1/-src, db_backups, ssyq-*.csv, /tmp/{idv,pwtool,pvenv,socksvenv,trae,tousphl,bingfa_new}.

## Provenance checks that cleared the way (reusable recipes)
- /proc cwd + fd scan for every candidate dir → zero hits = nothing live holds them.
- Grep other profiles' state stores for candidate names → zero refs (botA/botB idle, heartbeat trims only).
- Hermes `sessions/request_dump_*.json` timestamps pinned fresh dirs to the session active at 09:20–12:48 — our own profile's morning campaign session, already stopped → safe to retire.
- Fresh-today dirs (hucacc/cmsnt/epusdt cluster) were the day's campaign; archive preserved report + loot + cookies + takeover status before delete.

## Keep-tensions (judgment calls — disclose, don't silently decide)
- /tmp/tousphl — user's 归集 line with bcrypt cracking progress; kept.
- /tmp/bingfa_new — AI-security KB material possibly pending ingest; kept.
- mysqladmin false alarm: without credentials it prints "Access denied for user" on a perfectly alive server — verify via pgrep mysqld + ss :3306.
