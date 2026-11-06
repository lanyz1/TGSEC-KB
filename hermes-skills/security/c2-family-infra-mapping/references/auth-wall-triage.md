# Panel auth-wall triage (scam / MaaS panels)

Patterns observed across Chinese scam/MaaS panel families; use to size up a login wall fast and decide where to spend time.

## Flow shapes
- Express + React SPA behind a catch-all route; Bearer token kept in `localStorage` (`token`, `fc_token`, `auth_token`, …). Panels often ship a "server address" setting — one UI can point at multiple backends, so expect several hosts per family.
- Login: `POST /api/auth/login {"username","password"}`. Success may be gated: `{"success":true,"data":{"requiresTelegram2FA":true,"challengeId":"<hex>"}}` → `POST /api/auth/login-telegram-verify {"challengeId","code"}`; code = 6-char STRING; expires 300 s; challenge issuance is per-login.
- WS panel stream: `/ws/panel?token=<t>` (often another port, e.g. :8888). An upgrade that accepts any token and then stays silent is NOT access — treat the handshake only as intel (which fields it validates).
- Chinese server messages are machine-useful: `未登录` (auth gate), `用户名不能为空` / `缺少参数` (validation shape), `用户名或密码错误`, `登录失败次数过多，请稍后再试` (rate limit), `验证码错误` (2FA compare), `Token验证失败`.

## Rate limits
- Counters are usually per-IP (sometimes per-IP+username). Confirm scope: throttled on your IP but a fresh proxy IP immediately gets a normal response/challenge ⇒ per-IP.
- Rotate a proxy list (regional proxies when the panel filters foreign sources); pace requests; retire a burned exit until cooldown.
- Do not extrapolate lockout behavior across panels: one tolerated many wrong 2FA codes without locking; assume others lock after a few.

## Telegram 2FA
- The OTP is pushed to the operator's Telegram chat by the panel's notification bot. Without read access to that chat it is a hard wall: a uniform random 6-digit code is not brute-forceable, and each guess risks operator alerts. Triage, then stop.
- Cheap probes, one pass, seconds: `code` as number/bool/array/object (strict-type errors like `缺少参数` reveal the validation shape); metacharacter payloads in `code`/`challengeId` (SQL/NoSQL); timestamp-suffix guesses ONLY if the codegen smells lazy.
- Better pivots than grinding: other usernames may lack 2FA binding; sibling hosts / other brand boxes of the same family are usually softer.
- Assume every successful admin login pushes an OTP/alert — few attempts, paced, from proxies.

## What the wall still yields
- The SPA bundle documents the entire backend (endpoints, fields, flows) while logged out — mine it first.
- Unauthenticated responses still leak user-enumeration differences, limit semantics, and validation behavior.
