# PanGu Mail / cloud-mail (Cloudflare Workers + D1 + KV)

Worked example of the parent skill's procedure. Product: a Chinese webmail panel branded
"PanGu Mail", upstream repo `maillab/cloud-mail` (Cloudflare Workers, D1, KV, optional R2/S3).

## Identification

- `<title>` and the About page link straight to the upstream GitHub repo.
- An API error body containing `D1_TYPE_ERROR` announces the Workers + D1 architecture, which
  also means every DB parameter is a bound D1 prepared-statement value (so quote-based SQLi
  probes are a waste of time — test for **unbound** parameters instead, i.e. missing params).
- All API routes live under `/api/*`; the worker strips the prefix and re-enters the Hono app,
  so always compare against the *stripped* path when reasoning about middleware.

## Pinning the deployed tag

Three probes were enough to bracket it, then the source confirmed:

| probe | observation | conclusion |
|---|---|---|
| `GET /api/role/permTree` | 200 (route renamed to `/role/tree` in v3.0.0) | deployed <= v2.9.0 |
| `GET /api/allEmail/latest` | 404 (route added in v2.7.0) | deployed < v2.7.0 |
| `GET /api/oss/<key>` | `Cannot read properties of undefined (reading 'get')` — the direct `c.env.r2.get` form | deployed in v2.4.0–v2.6.0 |

Bonus signal: whether a permission entry exists in `requirePerms` differs between tags, so an
endpoint that returns 200 instead of 403 tells you the tag as reliably as a 404 does.

## Auth model (read this before probing anything)

1. JWT HS256, payload `{userId, token: <uuid>, iat}`.
2. Middleware verifies the signature, then loads KV `auth-uid:<userId>` and requires the JWT's
   `token` to be present in that record's `tokens` array.
3. Permission check: the role's perm keys are mapped to route paths; if the request path is
   not in that union **and** `user.email !== c.env.admin`, it returns 403.

**Consequence:** the only privilege escalation is controlling an account whose email equals
the `admin` env var. Everything else is role-driven, and forging a JWT is worthless without
both the secret and a live token from that user's KV record.

## Admin identity oracle

`POST /api/public/genToken` is excluded from the auth middleware and validates
`email === c.env.admin` **before** the password. Three distinguishable states:

- not the admin email -> "not admin"
- admin email but no user row -> "user not found"
- admin email, row present, wrong password -> "wrong password"

Sweeping a few thousand candidate emails produced zero hits, which is a real finding: with
this env var unset, **no account on the deployment can be admin**. Do not read that as "the
brute force failed" — a missing env var and a wrong guess produce identical responses.

## Permission gaps in the deployed release

Routes present but absent from the permission map, all reachable with a plain low-priv token:

- `GET /api/analysis/echarts` — aggregate counts only (user/email totals, top sender names).
  Useful for sizing the deployment, not for PII.
- `GET /api/role/permTree`, `GET /api/role/selectUse` — permission metadata.
- `PUT /api/user/restore` — restores the soft-delete flag for **any** userId. Executes, but
  only flips `isDel`; it does not touch status or role.
- `DELETE /api/allEmail/batchDelete` — destructive, filtered delete across all users,
  returns nothing. No read primitive.
- `PUT /api/account/setName`, `PUT /api/account/setAllReceive`, `PUT /api/email/read` — all
  re-scope by the caller's userId inside the service layer, so no IDOR.

None of them leak another user's mail. Record that rather than re-testing.

## Reading YOUR OWN mailbox (the OTP channel)

Your own mailbox is what makes an OTP chain work, and the read is easy to get wrong:

1. `POST /api/login {email, password}` -> `data.token`. Send it on later calls as a **raw**
   `Authorization` value — no `Bearer` prefix.
2. `GET /api/account/list` -> take `data[].accountId` for your own row.
3. `GET /api/email/list?accountId=<yourId>&emailId=0&timeSort=0&size=20&type=0&full=1`.

- **PITFALL — an empty or omitted `accountId` returns an EMPTY list, indistinguishable from "this
  mailbox received nothing".** Time was spent concluding the OTP never arrived when the call was
  simply missing the id. Take `accountId` from `/api/account/list` first, and after requesting a
  code confirm the list length actually changed instead of trusting a bare `{list:[],total:0}`.
- **PITFALL — parse the JSON, do not regex the raw body.** Message HTML is JSON-escaped in the list
  response, so a `"`-anchored regex over the raw text silently misses. Decode the JSON and read
  `data.list[].content`.
- **Code extraction:** the live pattern is `<span class="var0-0-3 varflag">(\d{6})</span>`. A bare
  `\b\d{6}\b` also matches **CSS colour literals and Vue scope ids** (`327681`, `307dff`, `179955`),
  which recur many times per message and are the classic false positive that makes an extractor grab
  the wrong six digits. Anchor on the `varflag` span, or at minimum drop known colour values.
- `验证码尚未失效！` on a repeat request means the platform cooldown is still live and the
  previously mailed code is the one to use — read the mailbox, do not wait for a new mail.

## Why the mail table is not reachable

- Every read path (`/api/email/list`, `/latest`, `/api/email/attList`) forces
  `email.user_id = <jwt userId>`; the `accountId` parameter is a *cursor* (`accountId > x`),
  not an ownership lookup, so scanning it returns empty, not other people's rows.
- `POST /api/public/emailList` has no user scoping at all, but sits behind a KV public token
  (`public_key:`) that is only minted by `/public/genToken`, which needs admin credentials.
  Note the middleware reads the token with a plain string compare, so an unset KV key is not
  bypassable with a missing header.
- `/api/telegram/getEmail/:token` is a self-verifying JWT route (`{emailId}` signed with the
  same secret) — no help without the secret.

## Storage read/write surface

- Unauthenticated object reads exist at `/static/<key>` and `/attachments/<key>`, but the
  key is `pathname.substring(1)`, i.e. it is **prefixed** — raw keys such as `auth-uid:<id>`
  or `public_key:` cannot be reached, and KV keys are literal so `..` does not traverse.
- `/api/oss/<key>` does take a raw key, but in this release version it calls `c.env.r2.get`
  directly and R2 is unbound, so it 502s. On a deployment that binds R2 or KV storage, the
  same route is an arbitrary KV/object read — worth re-testing per deployment.
- Write side: `saveSendAtt` re-derives the key as `attachments/ + sha256(content) + ext`, and
  inbound attachment parsing does the same. Only the extension is caller-controlled, which is
  not enough to escape the prefix. Confirmed dead, do not re-derive.

## Registration / session minting

- `GET /api/setting/websiteConfig` is **unauthenticated** and returns the whole site config:
  `siteKey` (the Turnstile sitekey), `r2Domain`, `domainList`, `registerVerify` / `regVerifyOpen`,
  `minEmailPrefix`. Read it first — it also names extra infrastructure for recon (the leaked
  `r2.<domain>` here put a second object-store endpoint on the map).
- `/api/register` is open but enforces Turnstile. It resolves the address **before** the captcha, so
  a duplicate answers `This Email is already registered` while a fresh one answers
  `Please verify that you are human` — a free mailbox-existence oracle needing no captcha solve and
  no token. (A too-short password is rejected with a length error first, so send a >=6-char dummy to
  reach the existence branch.) Note `domainList` is what the panel can MINT: a single-domain panel
  only issues its own addresses, which is often exactly what a platform-side registration whitelist
  demands.
- The OAuth `bindUser` route is auth-excluded and calls register with `oauth = true`, which
  forcibly sets `registerVerify = CLOSE` (bypassing Turnstile) and then logs in with
  `noVerifyPwd = true`. It requires a pre-existing unbound `oauth` row, which requires a real
  provider callback (the row cleanup runs daily), so it is only reachable when a provider is
  actually configured.
- `/api/init/:secret` compares against `jwt_secret`, so it doubles as a secret-confirmation
  oracle for a guessed default.
