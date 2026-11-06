# Controlled product mail OTP remint (cloud-mail class)

Use when the tenant runs a first-party webmail (often `mail.<tenant>`, cloud-mail forks) that the operator can open, and platform login consumes email OTP.

## Auth

- Prefer `POST /api/login` with `{email, password}` — sibling paths like `/api/user/login` may 404/empty.
- Authorization is usually the **raw JWT** in `Authorization` (no `Bearer ` prefix). Wrong scheme yields empty lists that look like “no mail”.
- List mailboxes: `GET /api/account/list` → take the correct `accountId` before list. Wrong id → `total:0`.

## Read newest OTP

1. Snapshot `max_email_id` from the inbox **before** each `getCode`.
2. List with full params: `accountId`, `size`, `type`, `full=1` (and/or `GET /api/email/latest`).
3. **Sort by `emailId` descending.** First-row / ascending order returns stale historical WQCHAT mails and burns the login window on dead codes.
4. Parse body/subject with `验证码[^\d]{0,12}(\d{4,6})` first; drop EngageLab noise `327681`.
5. Only accept codes from mails with `emailId > max_email_id` (or timestamp after the getCode stamp).

## Platform field split

| Step | Endpoint | Identity field |
|---|---|---|
| Send OTP | `…/userApi/getCode` | **`number`** = email/phone |
| Forgot / login | `…/userApi/forgotPassword`, `…/userApi/userLogin` | **`userName`** = email |

`getCode` with only `userName` often answers `请填写号码`. Login with only `number` fails schema.

## Double-OTP remint

1. `getCode` → wait → read **new** code A.
2. `forgotPassword` with `userName` + code A + `password`/`rePassword` (consumes A; `操作成功` with null data may still be fake — verify later).
3. `getCode` again → wait → read **newer** code B (id > A’s mail).
4. `userLogin` with `userName` + password + code B + correct `serverId`/`deviceId`.
5. Persist **`data.token` as TIM userSig** when it is `eJwt…`, plus any nested `access_token`.

One-code scripts that reuse A for login after forgot are a common false “OTP broken” path.

## Tenant check

Confirm `imAppid` / `serverId` from the login body before TIM destroy. Same mailbox on another server mints a different accid; cross-tenant destroy returns `10010`/`10015`.
