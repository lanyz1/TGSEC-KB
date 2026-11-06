# Guerrilla / grr.la OTP read (IM-overlay mail)

Use when `getCode` returns send-success / still-valid but the agent reports no OTP.

## Bind

```text
GET https://api.guerrillamail.com/ajax.php
  ?f=set_email_user&email_user=<local>&lang=en&site=grr.la
```

Keep the session cookie + `sid_token` from the JSON. The displayed address may be `*@guerrillamailblock.com` while the app still addresses `*@grr.la` — both map to the same inbox when `email_user` matches.

## Read order

1. Record `before_ts = now - small_skew` **before** calling app `getCode`.
2. App `getCode` with `number=<email>`, `type="2"`, correct `serverId`.
3. Sleep ~8–15s.
4. `get_email_list?offset=0&sid_token=…` (more reliable than bare `check_email` alone).
5. For each newest mail: `fetch_email?email_id=…&sid_token=…`.
6. Parse `mail_body`:
   - prefer `>(\d{6})<`
   - else word-boundary `\b(\d{6})\b`
   - drop EngageLab noise `327681`
7. Prefer mails with `mail_timestamp >= before_ts`. If only older mails exist, do **not** feed stale codes into login after a long cool — re-`getCode` instead.

## Failure mapping

| Symptom | Likely cause | Next |
|---|---|---|
| getCode 200, list empty | wrong `email_user` / site, or delay | re-bind site=grr.la; wait; re-list |
| list has WQCHAT, “no otp” | extract only checked subject/excerpt | always `fetch_email` + body regex |
| OTP parsed, login `账号或密码错误` | wrong password/type shape, or empty-pw path dead | one shape matrix max; forgot→verify; or stop identity |
| second shape → `登录过于频繁` | identity rate-lock | stop identity multi-hour; keep platform eyJ for reads |

## Do not

- Treat getCode success as proof login is unlocked.
- Walk the same OTP across many type/password bodies.
- Use an OTP older than the latest getCode window after multi-hour cools.
