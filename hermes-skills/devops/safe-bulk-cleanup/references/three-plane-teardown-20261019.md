# Three-plane teardown — 2026-10-19 (hutaocards / Saturney)

Use this when the owner asks 「彻底清理干净了吗」 after a stop/cleanup order. A clean process table proves only one plane.

## Plane 1 — local host

- Kill by exact PID from a `/proc` scan; never `pkill -f` (self-kill risk).
- `systemctl disable --now` is not final for units with `Restart=always`.
- **WARP repair that actually held:** `systemctl stop warp-svc` → `disable` → `rm -f /etc/systemd/system/multi-user.target.wants/warp-svc.service` → `ln -sf /dev/null /etc/systemd/system/warp-svc.service` → `daemon-reload` → kill PID. Verify **all** of: `is-active=inactive`, `is-enabled=masked`, symlink target `/dev/null`, `ps -C warp-svc` empty, `ss -lntp | grep :40000` empty. Re-check after a few seconds.
- `tor`: stop/disable/mask `tor` **and** `tor@default`; verify `9050`/`9051` gone. Do not touch pre-existing services the owner needs.
- Delete campaign `/tmp` payloads/session/cookie files, `screen`/`tmux`, temporary `/etc/hosts` entries, and campaign cron jobs. Check `~/.bash_history` for inline tokens.

## Plane 2 — target side

A stop order does not authorize production cleanup. If the owner explicitly says 「都清理」/「连证据一起抹」, attempt only documented delete routes and record every failure:

| object | attempted route | result |
|---|---|---|
| test user ID 29 / R22 Tester | `DELETE /admin/users/29` | 405; `/edit` 404; no UI delete → survives |
| product 1 `description` | overwrite was done earlier | original never captured → irreversible |
| footer 24 chars | overwrite was done earlier | original never captured → irreversible |
| test product image | hashed `.jpg` in storage | no delete API → survives |
| two ¥0 orders | status changed to cancelled | rows remain |

Before changing any target field, **capture the original value**. After an admin credential is rotated, a `302 → /login` from both Cloudflare and the origin is the stop signal: one canonical login attempt each, then stop. Do not brute-force or invent routes. A `DELETE` 405 + `/edit` 404 + login 302 means the target is **not** clean.

## Plane 3 — agent session history

- `~/.hermes/state.db` can be multi-GB and is separate from `/root/cases`. Case deletion does not scrub it.
- Probe schema before querying: `PRAGMA table_info(messages)` / `PRAGMA table_info(sessions)`. In one build `messages` has **no `session_id`**; assuming it fails.
- Read-only search for target name, token, cookie, test email. Tool-output rows often retain what reports no longer do.
- If asked to purge: `PRAGMA secure_delete=ON`; delete only named closed/cron sessions; `PRAGMA wal_checkpoint(TRUNCATE)`. Do not delete the live session from inside itself.
- `PRAGMA freelist_count` vs `page_count`: a 2.4GB DB with freelist≈0 is all live rows; `VACUUM` reclaims nothing. Purging is a content decision.

## Answer shape

> Local: processes/ports/cron/temp creds clean, units inactive+masked. Target: N residuals (exact IDs + why undeletable). Session DB: present/scrubbed.

If target or session residuals exist, the first word is **No**, not 「全干净」.
