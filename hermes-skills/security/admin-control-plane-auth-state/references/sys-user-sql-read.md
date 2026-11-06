# `sys_user` SQL read and write-primitive triage

Use when a login/API SQL injection can read the admin table but you need to know
whether it can write, and how to extract many rows without losing to throttling.

## 1. Identify the query shape

- Login `username` concatenated into SQL; password compared in PHP -> the login
  bypass is `' OR 1=1-- -`, but the injection is still one statement.
- `mysqli_query` (and most single-query APIs) does not allow stacked statements:
  `'; SELECT SLEEP(3);-- -` returns a syntax error near the second statement.
  If so, no `UPDATE sys_user SET password=...` through this injection.
- Test `SLEEP`/`BENCHMARK` on a valid row to confirm the injection is live; a
  syntax error at the second statement is the signature of a single-statement
  API, not a dead injection.

## 2. File-write branch

- Check `secure_file_priv`: `NULL` means `INTO OUTFILE` and `LOAD_FILE` are
  blocked. `''` means any directory; a path means only that directory.
- If `OUTFILE` works, the DB user needs `FILE` and the directory must be
  writable by `mysqld`; a web-root write is the next step.
- If `secure_file_priv=NULL`, no UDF and no `OUTFILE`, the SQLi is read-only;
  do not promise RCE from it.

## 3. Bulk read without losing to throttling

- `UNION` with the exact column count (30 observed) returns full rows; the
  visible columns depend on which slots the page reflects.
- For many rows, use `GROUP_CONCAT` into a TEXT column (e.g. `front_remark`) and
  batch ~50 rows per request. A short column truncates the payload.
- Per-row `LIMIT i,1` can be throttled hard (observed ~500 rows/196s); batch
  with `GROUP_CONCAT` and fall back to smaller groups when the response is cut.
- Keep the collection in a local file; do not print full rows with PII in the
  chat. Record counts/min/max IDs to prove coverage.

## 4. Hash extraction checklist

- Pull `username, password, status, token_version` for admin rows.
- A bcrypt hash is `$2a$`/`$2b$`/`$2y$` + cost + 53 chars; verify a known
  plaintext/hash pair before cracking.
- `token_version` is not a password; it is a revocation counter.
- Do not treat a `code` or `home_path` column as a login secret.

## 5. Decision tree

1. Stacked write possible? -> `UPDATE sys_user` / reset password, then log in.
2. File write possible? -> webshell / cron / config write.
3. Read-only + token live? -> use the token, do not crack.
4. Read-only + token dead? -> offline bcrypt, then report the gate.
5. No write and no crack? -> pivot to another control-plane surface; do not
   call the SQLi a root.
