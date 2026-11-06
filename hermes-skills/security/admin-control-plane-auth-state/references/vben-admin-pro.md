# Vben Admin Pro: token liveness, role hierarchy, admin API

Session-derived notes from an authorized Vben Admin Pro assessment. Use as a
checklist, not as a target-specific recipe. Replace `admin.example.com` with
the target; never store real tokens or passwords in notes.

## 1. Frontend chunks -> API map

Vben Admin Pro ships route constants and request paths in its JS chunks. Pull
the chunk that contains `/system/` or `/auth/` and extract paths, not just
looking at the rendered UI.

Observed routes (validate against the target's own chunks):

- Auth: `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/codes`.
- Admin CRUD: `/system/admin/list`, `/system/admin/{id}`,
  `POST /system/admin/{id}/password`, `/system/admin/{id}/freeze`,
  `/system/admin/{id}/force-logout`.
- Role/menu: `/system/role/list`, `/system/menu/all`.
- Settings: `/system/settings` (often 30+ business settings, no JWT secret).
- Members: `/member/list`, `/member/{id}`, `GET/POST /member/{id}/password`
  (GET can return a plaintext password if the backend is careless).
- Finance: `/finance/withdraw/list`, `/finance/withdraw/{id}/approve`,
  `/finance/pay-channel/list`.

Important route traps:

- The admin reset endpoint is `POST /system/admin/{id}/password`; a guessed
  `/system/user/resetPwd` or `/system/user/edit` may be 404. Use the chunk's
  exact path.
- `/system/user/list` may not exist even when `sys_user` is the backing table.
- `VITE_APP_NAMESPACE` / `VITE_APP_STORE_SECURE_KEY` are frontend namespace and
  storage keys, not the JWT signing secret. Do not feed them into HMAC tests as
  if they were the secret; a namespace value like `vben-fa-card` is only a
  dictionary candidate.

## 2. JWT liveness model

HS256 tokens observed with claims:

- `userId`, `username`, `roles` (e.g. `["group_admin"]`), `tokenVersion`,
  `iss`, `iat`, `exp`.

The server checks more than the signature:

- account `status` — a valid token for a disabled/deleted user returns
  "用户不存在或已禁用" (user does not exist or is disabled);
- `sys_user.token_version` — the DB value must match the JWT claim; incrementing
  it revokes all old tokens without changing the password;
- role/permission on the specific endpoint.

A token with `exp` six days out can therefore be dead. Conversely, a 401
"未登录" on an admin route means the auth filter rejected the request; a 200
with a JSON business error may mean you are authenticated but lack permission.
Test no-token, malformed-token, low-role-token, and real-token separately.

## 3. Role hierarchy and reset

Observed `sys_user` columns (MySQL):

`id, dept_id, username, password, token_version, real_name, avatar, email,
phone, gender, home_path, desc, status, timezone, last_login_at,
last_login_ip, created_at, updated_at, deleted_at, code, domain`.

- `password` is bcrypt (cost 12 in the observed case).
- `token_version` is the revocation counter.
- `code` can be a six-digit internal code, not a login password.
- `home_path`, `dept_id`, `roles` drive the admin UI; they do not grant
  super-admin by themselves.

Observed role ids:

- 1 = super admin (`sadmin`)
- 2 = group admin (`admin1`)
- 4 = operations/admin (`vadmin`)

A role-4 token successfully reset a role-2 account's password but could not
reset the role-1 account. Do not call a role-4 token a super-admin takeover.
A role-2 token reset by role 4 is useful only if that account is still active
and its tokenVersion still matches.

## 4. Reading `sys_user` through SQLi

- The login `username` was concatenated into SQL; the password was compared in
  PHP, so `' OR 1=1-- -` bypassed login but did not write.
- `mysqli_query` ran one statement only: a stacked `'; SELECT SLEEP(3);-- -`
  produced a syntax error at the second statement. No stacked `UPDATE`.
- `secure_file_priv=NULL` blocks `INTO OUTFILE` / `LOAD_FILE`; no UDF path.
- Use `UNION` to read full rows (30 columns observed). For bulk reads, put
  `GROUP_CONCAT` in a TEXT column slot (e.g. `front_remark`) and batch ~50 rows
  per request; per-row `LIMIT` was rate-limited to ~500 rows/196s.
- Before trusting a failed bcrypt crack, crack a known hash with its known
  plaintext using the same command. If the self-check fails, the hash file or
  extraction is wrong, not the password.

## 5. What "dead" looks like

In the observed engagement the account `admin1` had a valid HS256 token with
`roles:["group_admin"]` and ~6.5 days left, but its `status` was 0 and every
admin route said "user not found or disabled". Another token (`vadmin`, role 4)
read settings and withdrawals earlier, then the operator changed the password
and rotated the token; a later failed login overwrote the token file with
`null`. The old token was not recoverable from `/root`, `/tmp`, terminal
caches, or the session DB.

Lesson: capture the token once, immediately test it against a cheap
authenticated endpoint, and record its claims and the DB row state before doing
anything else. A token in a file is not a token in the server's session table.
