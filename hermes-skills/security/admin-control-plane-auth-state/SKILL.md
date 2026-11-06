---
name: admin-control-plane-auth-state
description: Use when an admin JWT is offline-valid but rejected live.
---

# Admin control-plane auth state

A valid JWT signature is not a live admin session. Admin control planes
usually also check account status, a token/session version, deletion, role,
and sometimes IP/UA binding. This skill is the checklist for proving or
disproving liveness before spending time on password cracking or declaring
"no auth bypass".

## When to use

- You have an admin JWT/token but the API says "user not found/disabled" or 401.
- A token worked earlier and stopped, with no password change.
- You found admin password-reset, member-password, settings, role, or withdraw
  endpoints and need to know whether a low-role token is enough.
- You have a DB read primitive and admin password hashes; you need to decide
  between token recovery, offline cracking, and SQL write.

## First: liveness, not forgery

1. Decode the token; record `userId`, `username`, `roles`, `tokenVersion`,
   `iss`, `iat`, `exp`. Do not print the token.
2. Establish an authenticated oracle endpoint. Compare:
   - no token -> 401/auth filter
   - malformed/expired token -> 401
   - real token -> business response or "user disabled"
   - low-role token -> permission/business error
   The difference between 401 and a business error is the difference between
   "auth is closed" and "you have a token but lack permission".
3. If you can read the user row (SQLi, backup, export, API), check `status`,
   `deleted_at`, and `token_version`. A token `tokenVersion` mismatch means
   revocation even if `exp` is in the future.
4. Check token caches. A later failed login can overwrite a previously valid
   token file with `null`; compare mtime and hash. Search `/root`, `/tmp`,
   terminal caches, and session DBs only when the token is worth recovering.
5. Check role hierarchy on reset/list endpoints. A lower role can often reset
   lower accounts but not the super admin; role 4 is not role 1. Test the exact
   endpoint the frontend uses (`POST /system/admin/{id}/password`), not a
   guessed `/system/user/resetPwd` that may 404.

## If the token is dead

- Do not immediately pivot to forging: a valid signature with a stale
  `tokenVersion` is still dead. Forging only helps if you know the current
  tokenVersion and the secret.
- Offline bcrypt recovery is the next branch for admin hashes. See
  `references/bcrypt-cpu-john.md` for CPU john/hashcat discipline and the
  known-plaintext self-check.
- If you have SQLi, test the write primitive before promising `UPDATE
  sys_user`: stacked statements may be disabled; `secure_file_priv=NULL` may
  block file writes. See `references/sys-user-sql-read.md`.
- If none of those work, report the control-plane gate honestly; do not call a
  role-4 token a super-admin takeover.

## Pitfalls

- "User not found or disabled" can mean a valid token for a disabled account,
  not a bad token. Check the account, not just the signature.
- `token_version` increments are a revocation mechanism; old tokens cannot be
  revived by re-signing without the current version.
- Login error text may name stale/decoy users; enumerate `sys_user` rows.
- A token file with a future `exp` can be overwritten by a failed login later;
  the old token may be gone from disk.
- `/system/admin/5/password` without a token is 401; do not mistake the auth
  filter for an absent endpoint.
- Role hierarchy is server-side; a role-4 token resetting a role-2 account does
  not imply it can reset role 1.
- A "0 cracked" result is only valid after a known-hash/known-plaintext
  self-check passes.

## Scope gate

- Only the named target and its true related stack: same A-record IP or a real
  homepage JS/iframe connection. A shared app-distribution bucket or a sister
  brand is not enough; do not attack the sister app.
- If the user sends a new target and immediately says "搞错了/发错了/继续任务",
  treat the new target as mis-sent: do not scan, log in, or touch it; continue
  the original engagement. See `references/scope-and-mis-sent.md`.

## References

- `references/vben-admin-pro.md` — Vben Admin Pro chunk routes, `sys_user`
  columns, tokenVersion, role ids, reset endpoint.
- `references/bcrypt-cpu-john.md` — bcrypt on CPU, john `--restore`, false
  negatives, background jobs.
- `references/sys-user-sql-read.md` — single-statement SQLi, UNION/GROUP_CONCAT
  batching, file-write triage.
- `references/scope-and-mis-sent.md` — target relation and mis-sent-target rule.
- `references/app-distribution-bucket.md` — WGT/uni-app distribution bucket recon
  and sister-brand scope.
